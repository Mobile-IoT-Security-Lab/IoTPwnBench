package org.iotbench.fixture;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/** Shared bounded framing, corrected variant of CWE-20. The label follows its contract. */
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
                // The contract is [A-Za-z0-9_-]{1,128}, so no command syntax reaches a JAR.
                for (int j = 0; j < label.length(); j++) {
                    char c = label.charAt(j);
                    boolean allowed = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                            || (c >= '0' && c <= '9') || c == '_' || c == '-';
                    if (!allowed) {
                        throw new IllegalArgumentException("invalid label characters");
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
