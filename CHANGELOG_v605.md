# v6.0.6

Windows SQLite test-hygiene patch.

- Close helper-returned SQLite connections in professor audit tests.
- Close thread-local SQLite connection in desktop regression test.
- Preserve Windows-safe temporary-directory cleanup.
