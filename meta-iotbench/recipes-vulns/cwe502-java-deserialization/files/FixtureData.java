package org.iotbench.fixture.deserialization;

import java.io.Serializable;

/** The sole application request type: synthetic sensor identifier and reading. */
public final class FixtureData implements Serializable {
    private static final long serialVersionUID = 1L;
    public final String sensor;
    public final int reading;

    public FixtureData(String sensor, int reading) {
        this.sensor = sensor;
        this.reading = reading;
    }
}
