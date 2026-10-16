package org.iotbench.fixture;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/** Local application backend; the shared dashboard is its only network gateway. */
public final class FixtureWebService {
    private FixtureWebService() { }

    public static void main(String[] args) throws IOException {
        // Bound requests and responses, including clients that stop sending.
        System.setProperty("sun.net.httpserver.maxReqTime", "5");
        System.setProperty("sun.net.httpserver.maxRspTime", "5");
        System.setProperty("jdk.httpserver.maxConnections", "8");
        int port = Integer.getInteger("iotbench.fixture.port", 18089);
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 8);
        server.createContext("/lookup", FixtureWebService::handle);
        server.setExecutor(new ThreadPoolExecutor(2, 2, 0, TimeUnit.SECONDS,
                new ArrayBlockingQueue<Runnable>(8), new ThreadPoolExecutor.AbortPolicy()));
        server.start();
        System.out.println("JAVA_SQL_FIXTURE_LISTENING=127.0.0.1:" + server.getAddress().getPort());
    }

    private static void handle(HttpExchange exchange) throws IOException {
        try (exchange) {
            if (!exchange.getRequestURI().toString().equals("/lookup")) {
                respond(exchange, 404, "Not found\n");
                return;
            }
            if (!exchange.getRequestMethod().equals("POST")) {
                exchange.getResponseHeaders().set("Allow", "POST");
                respond(exchange, 405, "POST required\n");
                return;
            }
            byte[] body = exchange.getRequestBody().readNBytes(961);
            if (body.length > 960) {
                respond(exchange, 413, "Record name too long\n");
                return;
            }
            try {
                String input = StandardCharsets.UTF_8.newDecoder()
                        .onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT)
                        .decode(ByteBuffer.wrap(body)).toString();
                // The same Java operation constructs and executes SQL for both interfaces.
                respond(exchange, 200, FixtureDbQuery.lookup(input));
            } catch (CharacterCodingException | IllegalArgumentException e) {
                respond(exchange, 422, "Invalid record name\n");
            } catch (SQLException | ClassNotFoundException e) {
                respond(exchange, 400, "Synthetic fixture lookup failed\n");
            }
        }
    }

    private static void respond(HttpExchange exchange, int status, String output) throws IOException {
        byte[] bytes = output.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "text/plain; charset=utf-8");
        exchange.getResponseHeaders().set("X-Content-Type-Options", "nosniff");
        exchange.sendResponseHeaders(status, bytes.length == 0 ? -1 : bytes.length);
        exchange.getResponseBody().write(bytes);
    }
}
