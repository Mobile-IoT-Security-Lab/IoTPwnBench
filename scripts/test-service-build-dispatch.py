#!/usr/bin/env python3
"""Verify real wrapper dispatch and refusal controls for the three service fixtures."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
FAMILIES={
    "cwe276-bad-write-rights":"IOTBENCH_ENABLE_FTP_WRITE_FIXTURE",
    "cwe798-unencrypted-traffic":"IOTBENCH_ENABLE_TELNET_FIXTURE",
    "cwe798-sudo-environment":"IOTBENCH_ENABLE_SUDO_ENV_FIXTURE",
}

def main():
    with tempfile.TemporaryDirectory(prefix="service-dispatch-") as temporary:
        work=Path(temporary)
        bindir=work/"bin";bindir.mkdir()
        recorder=bindir/"bitbake"
        recorder.write_text("""#!/usr/bin/python3
import json,os,sys
from pathlib import Path
assert sys.argv[1]=='-r',sys.argv
conf=Path(sys.argv[2])
Path(os.environ['DISPATCH_RESULT']).write_text(json.dumps({'argv':sys.argv[1:],'conf':conf.read_text(),'path':str(conf)}))
sys.exit(39)
""")
        recorder.chmod(0o755)
        source=(ROOT/"scripts/container-build-and-export.sh").read_text()
        assert source.count("source /opt/yocto/yocto-env.sh")==1
        wrapper=work/"build.sh"
        wrapper.write_text(source.replace("source /opt/yocto/yocto-env.sh",": # No Yocto environment in dispatch-only tests"))
        result_path=work/"result.json"
        base={k:v for k,v in os.environ.items() if not k.startswith("IOTBENCH_ENABLE_")}
        base.update(PATH=str(bindir)+os.pathsep+base["PATH"],DISPATCH_RESULT=str(result_path),TMPDIR=str(work))
        count=0
        for suffix,flag in FAMILIES.items():
            recipes=sorted((ROOT/"meta-iotbench/recipes-images").glob("iotbench-*-"+suffix+".bb"))
            assert len(recipes)==11
            for recipe in recipes:
                firmware=recipe.stem.removeprefix("iotbench-")
                for label,changes,accepted in [
                    ("enabled",{flag:"1","IOTBENCH_BUILD_MODE":"fixture"},True),
                    ("disabled",{flag:"0","IOTBENCH_BUILD_MODE":"fixture"},False),
                    ("production",{flag:"1","IOTBENCH_BUILD_MODE":"production"},False),
                    ("mixed",{flag:"1","IOTBENCH_BUILD_MODE":"fixture","IOTBENCH_ENABLE_REST_FIXTURE":"1"},False)]:
                    if result_path.exists(): result_path.unlink()
                    result=subprocess.run(["bash",str(wrapper)],env=dict(base,FIRMWARE=firmware,**changes),
                                          capture_output=True,text=True,timeout=15)
                    assert result.returncode==(39 if accepted else 1),(firmware,label,result.returncode,result.stderr)
                    if accepted:
                        data=json.loads(result_path.read_text())
                        assert data["argv"][-1]=="iotbench-"+firmware
                        assert flag+' = "1"' in data["conf"]
                        assert 'IOTBENCH_BUILD_MODE = "fixture"' in data["conf"]
                        if flag=="IOTBENCH_ENABLE_FTP_WRITE_FIXTURE":
                            assert 'DISTRO_FEATURES:append = " pam systemd"' in data["conf"]
                        assert not Path(data["path"]).exists(),"Temporary BitBake config leaked"
                    else:
                        assert not result_path.exists(),"Rejected mode invoked BitBake"
                    count+=1
        catalog=work/"catalog";(catalog/"scripts").mkdir(parents=True)
        (catalog/"meta-iotbench").mkdir()
        (catalog/"meta-iotbench/recipes-images").symlink_to(ROOT/"meta-iotbench/recipes-images",target_is_directory=True)
        (catalog/"scripts/build-all.sh").write_text((ROOT/"scripts/build-all.sh").read_text())
        docker=bindir/"docker"
        docker.write_text("""#!/usr/bin/python3
import json,os,sys
with open(os.environ['DISPATCH_RESULT'],'a') as out:
    out.write(json.dumps({'firmware':os.environ['FIRMWARE'],'machine':os.environ['YOCTO_MACHINE'],'argv':sys.argv[1:]})+'\\n')
""")
        docker.chmod(0o755)
        for enabled in (False,True):
            result_path.unlink(missing_ok=True)
            env=dict(base,MACHINES="qemuarm64")
            if enabled: env.update({flag:"1" for flag in FAMILIES.values()})
            subprocess.run(["sh",str(catalog/"scripts/build-all.sh")],env=env,capture_output=True,text=True,check=True,timeout=30)
            rows=[json.loads(l) for l in result_path.read_text().splitlines()]
            selected=[r for r in rows if any(r["firmware"].endswith("-"+s) for s in FAMILIES)]
            assert len(selected)==(33 if enabled else 0),(enabled,len(selected))
            for row in selected:
                flag=next(f for suffix,f in FAMILIES.items() if row["firmware"].endswith("-"+suffix))
                assert flag+"=1" in row["argv"]
                assert "IOTBENCH_BUILD_MODE=fixture" in row["argv"]
                assert row["machine"]=="qemuarm64"
                assert len([a for a in row["argv"] if a.startswith("IOTBENCH_ENABLE_")])==1
        print("PASS bulk catalog: 33 service images opt in independently and stay excluded by default")
        print(f"PASS {count} service dispatch cases across 33 images: explicit opt-in, production/mixed refusal and config cleanup")

if __name__=="__main__": main()
