package org.iotbench.fixture.deserialization;

import java.io.ByteArrayInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InvalidClassException;
import java.io.ObjectInputFilter;
import java.io.ObjectInputStream;
import java.io.StreamCorruptedException;

/** Opt-in fixture, corrected variant of CWE-502. Only the expected types are accepted. */
public final class FixtureDeserialize {
    public static final int MAX_BYTES = 4096;
    public static final int MAX_DEPTH = 8;
    public static final int MAX_REFERENCES = 32;
    public static final int MAX_ARRAY = 16;

    private FixtureDeserialize() { }

    public static ObjectInputFilter resourceLimits() {
        return info -> {
            if (info.streamBytes() > MAX_BYTES || info.depth() > MAX_DEPTH
                    || info.references() > MAX_REFERENCES || info.arrayLength() > MAX_ARRAY) {
                return ObjectInputFilter.Status.REJECTED;
            }
            // Type allowlist at the reconstruction boundary.
            Class<?> type = info.serialClass();
            if (type != null) {
                while (type.isArray()) {
                    type = type.getComponentType();
                }
                if (!type.isPrimitive() && type != FixtureData.class && type != String.class) {
                    return ObjectInputFilter.Status.REJECTED;
                }
            }
            return ObjectInputFilter.Status.UNDECIDED;
        };
    }

    /** Rejections compose with the stream/JVM filter; no global settings change. */
    public static void installResourceLimits(ObjectInputStream stream) {
        ObjectInputFilter limits = resourceLimits();
        ObjectInputFilter existing = stream.getObjectInputFilter();
        stream.setObjectInputFilter(existing == null ? limits : ObjectInputFilter.merge(existing, limits));
    }

    /** Read at most MAX_BYTES+1 bytes before constructing any object. EOF frames one request. */
    public static String process(InputStream source) throws IOException, ClassNotFoundException {
        byte[] bytes = source.readNBytes(MAX_BYTES + 1);
        if (bytes.length == 0) {
            return "EMPTY_INPUT";
        }
        if (bytes.length > MAX_BYTES) {
            return "INPUT_TOO_LARGE";
        }
        try (ObjectInputStream stream = new ObjectInputStream(new ByteArrayInputStream(bytes))) {
            installResourceLimits(stream);
            Object object = stream.readObject(); // Types outside the allowlist are rejected before this returns.
            if (!(object instanceof FixtureData)) {
                return "UNEXPECTED_TYPE";
            }
            FixtureData data = (FixtureData) object;
            if (data.sensor == null || !data.sensor.matches("[A-Za-z0-9_-]{1,32}")
                    || data.reading < -100 || data.reading > 100) {
                return "INVALID_DATA";
            }
            return "OK sensor=" + data.sensor + " reading=" + data.reading;
        }
    }

    public static void main(String[] args) {
        if (args.length != 1 || !"--fixture-test".equals(args[0])
                || !"1".equals(System.getenv("IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE"))) {
            System.err.println("FIXTURE_DISABLED");
            System.exit(64);
        }
        FixtureMarker.reset();
        String result;
        try {
            result = process(System.in);
        } catch (InvalidClassException exception) {
            result = "FILTER_REJECTED";
        } catch (EOFException exception) {
            result = "TRUNCATED_STREAM";
        } catch (StreamCorruptedException exception) {
            result = "INVALID_STREAM";
        } catch (ClassNotFoundException exception) {
            result = "UNKNOWN_CLASS";
        } catch (IOException exception) {
            result = "INVALID_STREAM";
        } catch (IllegalStateException exception) {
            result = "FILTER_CONFIGURATION";
        }
        System.out.println(result);
        System.exit(result.startsWith("OK ") ? 0 : 2);
    }
}
