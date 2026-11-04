require recipes-vulns/cwe122-smartspeaker-id3-overflow/cwe122-smartspeaker-id3-overflow_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-122 smart speaker ID3 heap overflow"
DESCRIPTION = "Corrected twin of cwe122-smartspeaker-id3-overflow. The ID3 length is checked against the 64-byte title field. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
