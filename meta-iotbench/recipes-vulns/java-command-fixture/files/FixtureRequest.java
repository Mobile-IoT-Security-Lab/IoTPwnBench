package org.iotbench.fixture;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/** Shared bounded framing, with exactly one deliberately incomplete field check. */
final class FixtureRequest {
    static final Path WORK = Path.of("/work");
    private FixtureRequest() { }

    static String read(String[] args) throws IOException {
        if (args.length != 1 || !"--fixture-test".equals(args[0])
                || !"1".equals(System.getenv("IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE"))) {
            throw new IllegalArgumentException("explicit fixture configuration required");
        }
        if (!Path.of("").toAbsolutePath().normalize().equals(WORK)) {
            throw new IllegalArgumentException("fixed disposable /work directory required");
        }
        // Exactly one ASCII request: label=<1..128 printable bytes> LF EOF.
        // This byte loop has a fixed upper bound, including for missing LF.
        ByteArrayOutputStream request = new ByteArrayOutputStream();
        for (int i = 0; i < 136; i++) {
            int value = System.in.read();
            if (value == -1) {
                byte[] bytes = request.toByteArray();
                if (bytes.length < 8 || bytes[bytes.length - 1] != '\n') {
                    throw new IllegalArgumentException("invalid request framing");
                }
                String line = new String(bytes, 0, bytes.length - 1, StandardCharsets.US_ASCII);
                if (!line.startsWith("label=")) {
                    throw new IllegalArgumentException("expected label field");
                }
                String label = line.substring(6);
                if (label.isEmpty() || label.length() > 128) {
                    throw new IllegalArgumentException("invalid label length");
                }
                // INTENTIONAL DEFECT (CWE-20 contributor): the contract is
                // [A-Za-z0-9_-]{1,128}, but only printable ASCII is checked.
                // Thus command syntax reaches the one construction site in each JAR.
                for (int j = 0; j < label.length(); j++) {
                    if (label.charAt(j) < 32 || label.charAt(j) > 126) {
                        throw new IllegalArgumentException("invalid label encoding");
                    }
                }
                return label;
            }
            if (value > 127) {
                throw new IllegalArgumentException("non-ASCII request");
            }
            request.write(value);
        }
        throw new IllegalArgumentException("request too long");
    }

    static void write(String name, String value) throws IOException {
        // Only interpreter-owned constant filenames reach this function.
        Files.writeString(WORK.resolve(name), value, StandardCharsets.US_ASCII,
                StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
    }
}
