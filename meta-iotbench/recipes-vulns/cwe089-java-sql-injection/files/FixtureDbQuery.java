package org.iotbench.fixture;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Properties;

/** Intentionally vulnerable, local synthetic research fixture: CWE-89. */
public final class FixtureDbQuery {
    private FixtureDbQuery() { }

    public static void main(String[] args) {
        byte[] notice = ("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — "
                + "LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT\n").getBytes(StandardCharsets.UTF_8);
        System.err.write(notice, 0, notice.length);
        if (args.length != 1 || args[0].isEmpty() || args[0].length() > 240) {
            System.err.println("Usage: java -jar fixture-db-query.jar RECORD_NAME (1..240 characters)");
            System.exit(2);
            return;
        }
        String input = args[0];
        try {
            System.out.print(lookup(input));
        } catch (SQLException | IOException | ClassNotFoundException e) {
            System.err.println("Synthetic fixture lookup failed");
            System.exit(1);
        }
    }

    /** Shared application operation used by the CLI and local web backend. */
    public static String lookup(String input) throws SQLException, IOException, ClassNotFoundException {
        if (input.isEmpty() || input.length() > 240) {
            throw new IllegalArgumentException("Expected a record name of 1..240 characters");
        }
        // INTENTIONAL CWE-89: input becomes SQL syntax, with no parameter binding
        // or SQL escaping. Keep this direct source-to-sink path for analysis.
        String query = "SELECT record_name, record_value FROM fixture_records "
                + "WHERE visibility = 'public' AND record_name = '" + input + "' ORDER BY id;";

        StringBuilder output = new StringBuilder();
        Properties fixture = new Properties();
        try (InputStream config = FixtureDbQuery.class.getResourceAsStream("/fixture.properties")) {
            if (config == null) {
                throw new IOException("Missing firmware fixture configuration");
            }
            fixture.load(config);
            // Only packaged configuration selects the database and native driver.
            System.setProperty("org.sqlite.lib.path", fixture.getProperty("driver.path"));
            Class.forName("org.sqlite.JDBC");
            Properties options = new Properties();
            options.setProperty("open_mode", "1"); // SQLITE_OPEN_READONLY
            options.setProperty("enable_load_extension", "false");
            try (Connection connection = DriverManager.getConnection(fixture.getProperty("database.url"), options);
                 Statement stmt = connection.createStatement()) {
                if (!connection.isReadOnly()) {
                    throw new SQLException("Fixture database must be read-only");
                }
                stmt.setMaxRows(16);
                stmt.setQueryTimeout(2);
                try (ResultSet rs = stmt.executeQuery(query)) {
                    while (rs.next()) {
                        output.append(rs.getString("record_name")).append('|')
                                .append(rs.getString("record_value")).append('\n');
                    }
                }
            }
        }
        return output.toString();
    }
}
