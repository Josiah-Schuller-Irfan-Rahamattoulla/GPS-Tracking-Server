-- Status LEDs on tracker hardware (default off when installed in vehicle).
ALTER TABLE devices ADD COLUMN IF NOT EXISTS leds_enabled BOOLEAN DEFAULT FALSE;
