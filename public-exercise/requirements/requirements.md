# ARC Counter Smoke Test

Use ARC to build an extremely small counter application for verifying the metered
competition submission and leaderboard pipeline.

This exercise exists to check the run contract end to end — package, upload,
extract, run the agent, deploy the generated application and evaluate it. It is
deliberately tiny so that a full local round trip takes seconds.

## REQ-1 Counter controls

**Type:** ATOMIC
**Dependencies:** None

The home page displays the current count, initially `0`, and buttons named
`Increment` and `Decrement`. Increment increases the displayed count by one and
Decrement decreases it by one. The count display has the test id `count`. No
styling or layout is required.

**Scenarios:**

- Increment and decrement the count
  - **GIVEN:** The visitor opens the home page and the displayed count is 0.
  - **THEN:** Buttons named "Increment" and "Decrement" are visible.
  - **WHEN:** The visitor clicks Increment twice.
  - **THEN:** The displayed count is 2.
  - **WHEN:** The visitor clicks Decrement three times.
  - **THEN:** The displayed count is -1.
