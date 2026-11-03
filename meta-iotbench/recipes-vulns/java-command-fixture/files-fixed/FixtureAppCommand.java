package org.iotbench.fixture;

import java.io.IOException;

/** Corrected variant of CWE-77, independent of operating-system command execution. */
public final class FixtureAppCommand {
    private FixtureAppCommand() { }

    public static void main(String[] args) throws IOException {
        final String label;
        try {
            label = FixtureRequest.read(args);
        } catch (IllegalArgumentException error) {
            System.err.println(error.getMessage());
            System.exit(2);
            return;
        }
        // FixtureRequest accepts only the label contract, so the label cannot add a statement.
        String command = "record " + label;
        try {
            interpret(command);
        } catch (IllegalArgumentException error) {
            System.err.println(error.getMessage());
            System.exit(3);
        }
    }

    // Grammar: program := statement (';' statement)*
    // statement := 'record ' printable-text | 'mark'
    // No quoting, escapes, substitutions, paths, loops or OS commands.
    private static void interpret(String program) throws IOException {
        String[] statements = program.split(";", -1);
        // Validate the entire program before producing output.
        boolean record = false;
        boolean mark = false;
        for (String statement : statements) {
            if (statement.startsWith("record ") && statement.length() > 7 && !record) {
                record = true;
            } else if (statement.equals("mark") && !mark) {
                mark = true;
            } else {
                throw new IllegalArgumentException("unknown or duplicate statement");
            }
        }
        for (String statement : statements) {
            if (statement.equals("mark")) {
                FixtureRequest.write("app-marker.txt", "JAVA_APP_MARKER\n");
            } else {
                FixtureRequest.write("normal.txt", statement.substring(7) + "\n");
            }
        }
    }
}
