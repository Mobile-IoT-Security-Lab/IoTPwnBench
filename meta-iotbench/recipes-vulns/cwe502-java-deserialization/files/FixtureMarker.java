package org.iotbench.fixture.deserialization;

import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.Serializable;

/** Benchmark-only class. Excluded together with the entire fixture in production. */
public final class FixtureMarker implements Serializable {
    private static final long serialVersionUID = 1L;
    private static int events;

    private void readObject(ObjectInputStream input) throws IOException, ClassNotFoundException {
        input.defaultReadObject();
        events++; // Harmless in-memory event; no I/O or other side effects.
    }

    public static int eventCount() {
        return events;
    }

    public static void reset() {
        events = 0;
    }
}
