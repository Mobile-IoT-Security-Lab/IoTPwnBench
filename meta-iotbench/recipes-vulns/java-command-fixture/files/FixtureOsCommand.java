package org.iotbench.fixture;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

/** CWE-78 (broader CWE-77); only run under the external isolation harness. */
public final class FixtureOsCommand {
    private FixtureOsCommand() { }

    public static void main(String[] args) throws IOException, InterruptedException {
        final String label;
        try {
            label = FixtureRequest.read(args);
        } catch (IllegalArgumentException error) {
            System.err.println(error.getMessage());
            System.exit(2);
            return;
        }
        // Intended operation: record one synthetic label in normal.txt.
        // The single incomplete validation in FixtureRequest permits quote
        // termination and a second shell command here. This is NOT Runtime.exec(String).
        String command = "printf '%s\\n' '" + label + "' > normal.txt";
        ProcessBuilder builder = new ProcessBuilder("/bin/sh", "-c", command);
        builder.directory(FixtureRequest.WORK.toFile());
        builder.environment().clear();
        builder.environment().put("PATH", "/nonexistent");
        builder.environment().put("LC_ALL", "C");
        builder.redirectOutput(ProcessBuilder.Redirect.DISCARD);
        builder.redirectError(ProcessBuilder.Redirect.DISCARD);
        Process child = builder.start();
        child.getOutputStream().close();
        try {
            if (!child.waitFor(2, TimeUnit.SECONDS)) {
                throw new IOException("shell timeout");
            }
            if (child.exitValue() != 0) {
                System.exit(3);
            }
        } finally {
            child.descendants().forEach(ProcessHandle::destroyForcibly);
            child.destroyForcibly();
        }
    }
}
