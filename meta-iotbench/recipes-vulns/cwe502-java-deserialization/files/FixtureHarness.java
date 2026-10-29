package org.iotbench.fixture.deserialization;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InvalidClassException;
import java.io.ObjectInputFilter;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.Arrays;

/** Test-only generator and independent in-process observer, outside the fixture JAR. */
public final class FixtureHarness {
    private FixtureHarness() { }

    public static byte[] generate(String name) throws Exception {
        Object value;
        switch (name) {
            case "normal": value = new FixtureData("sensor_01", 23); break;
            case "marker": value = new FixtureMarker(); break;
            case "invalid-data": value = new FixtureData("invalid sensor", 23); break;
            case "null": value = null; break;
            case "array-at-limit": value = new byte[FixtureDeserialize.MAX_ARRAY]; break;
            case "array-over-limit": value = new byte[FixtureDeserialize.MAX_ARRAY + 1]; break;
            case "depth-at-limit":
            case "depth-over-limit":
                value = new byte[0];
                int depth = FixtureDeserialize.MAX_DEPTH + (name.equals("depth-over-limit") ? 1 : 0);
                for (int index = 1; index < depth; index++) {
                    value = new Object[] {value};
                }
                break;
            case "references-over-limit":
                Object[] refs = new Object[16];
                byte[] shared = new byte[0];
                for (int index = 0; index < refs.length; index++) {
                    refs[index] = new Object[] {shared};
                }
                value = refs;
                break;
            case "bytes-at-limit":
            case "bytes-over-limit":
                value = new FixtureMarker();
                break;
            default: throw new IllegalArgumentException("unknown synthetic input: " + name);
        }
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ObjectOutputStream output = new ObjectOutputStream(bytes)) {
            output.writeObject(value);
        }
        if (name.startsWith("bytes-")) {
            // The protocol consumes one root object; inert trailing bytes are ignored.
            return Arrays.copyOf(bytes.toByteArray(), FixtureDeserialize.MAX_BYTES
                    + (name.equals("bytes-over-limit") ? 1 : 0));
        }
        return bytes.toByteArray();
    }

    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    /** Corrected comparison lives only in this harness. Resource/JVM restrictions remain. */
    private static Object allowlisted(byte[] bytes) throws Exception {
        try (ObjectInputStream stream = new ObjectInputStream(new ByteArrayInputStream(bytes))) {
            ObjectInputFilter allowlist = info -> {
                Class<?> type = info.serialClass();
                if (type == null) {
                    return ObjectInputFilter.Status.UNDECIDED;
                }
                return type == FixtureData.class || type == String.class
                        ? ObjectInputFilter.Status.ALLOWED : ObjectInputFilter.Status.REJECTED;
            };
            ObjectInputFilter policy = ObjectInputFilter.merge(FixtureDeserialize.resourceLimits(), allowlist);
            ObjectInputFilter existing = stream.getObjectInputFilter();
            stream.setObjectInputFilter(existing == null ? policy : ObjectInputFilter.merge(existing, policy));
            return stream.readObject();
        }
    }

    private static void observe() throws Exception {
        byte[] marker = generate("marker");
        // Multiple requests in the same JVM prove that state is explicitly reset.
        for (int repeat = 0; repeat < 2; repeat++) {
            FixtureMarker.reset();
            String result = FixtureDeserialize.process(new ByteArrayInputStream(marker));
            check(FixtureMarker.eventCount() == 1, "callback event missing before rejection");
            check(result.equals("UNEXPECTED_TYPE"), "unexpected application response");
            FixtureMarker.reset();
            try {
                allowlisted(marker);
                throw new AssertionError("allowlist accepted marker");
            } catch (InvalidClassException expected) {
                check(FixtureMarker.eventCount() == 0, "allowlist ran marker callback");
            }
            Object normal = allowlisted(generate("normal"));
            check(normal instanceof FixtureData && ((FixtureData) normal).reading == 23,
                    "allowlist rejected intended data");
            check(FixtureMarker.eventCount() == 0, "marker state leaked");
        }
        // The early byte bound must also prevent callbacks on an oversized valid prefix.
        FixtureMarker.reset();
        check(FixtureDeserialize.process(new ByteArrayInputStream(generate("bytes-over-limit")))
                .equals("INPUT_TOO_LARGE"), "byte bound missing");
        check(FixtureMarker.eventCount() == 0, "oversized input executed callback");
        System.out.println("OBSERVED marker_events=1 rejected_after_callback=true allowlist_events=0 reset=true oversized_events=0");
    }

    private static void observeGlobalFilter() throws Exception {
        FixtureMarker.reset();
        try {
            FixtureDeserialize.process(new ByteArrayInputStream(generate("marker")));
            throw new AssertionError("existing JVM rejection was lost");
        } catch (InvalidClassException expected) {
            check(FixtureMarker.eventCount() == 0, "existing JVM filter ran marker callback");
        }
        System.out.println("OBSERVED global_filter_events=0");
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 2 && args[0].equals("generate")) {
            System.out.write(generate(args[1]));
        } else if (args.length == 1 && args[0].equals("observe")) {
            observe();
        } else if (args.length == 1 && args[0].equals("observe-global")) {
            observeGlobalFilter();
        } else {
            throw new IllegalArgumentException("generate <vector> | observe");
        }
    }
}
