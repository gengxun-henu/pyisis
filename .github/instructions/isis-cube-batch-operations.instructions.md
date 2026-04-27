---
description: "Use when editing Python/C++ code that repeatedly opens ISIS Cube files, performs projection/camera/world-coordinate conversion, reads many windows from the same cube, or loops over many sample/line or ground-coordinate pairs. Keywords: Cube open reuse, projection batching, set_world, projected XY, sample line, coordinate conversion, bulk coordinate transform, camera lifecycle, Brick reuse, LineManager batching."
applyTo: "{src/**/*.{cpp,h},python/**/*.py,examples/**/*.py,tests/unitTest/**/*.py}"
---

# ISIS Cube Batch Operation Rules

Use these rules when code needs ISIS cube-backed geometry or raster operations for more than one coordinate pair, point, window, or transform.

## Core rule

- If multiple operations target the **same ISIS cube**, do **not** open and close that cube inside the per-point or per-window loop.
- Prefer this order:
  1. open the cube once
  2. create or fetch reusable state once when possible, such as `cube.projection()`, `cube.camera()`, or other cube-derived helper objects
  3. process as many coordinate pairs, windows, or conversions as possible in a batch-style loop
  4. close the cube once in `finally` / RAII cleanup

## Coordinate-conversion guidance

- For repeated sample/line -> projected XY, projected XY -> sample/line, sample/line -> ground, or similar geometry transforms on the same cube, prefer a helper that accepts:
  - an already opened cube, or
  - an already created projection/camera object,
  plus a collection of points
- If the Python-facing ISIS API only exposes **single-point** methods such as `set_world(...)`, `set_coordinate(...)`, `set_universal_ground(...)`, or camera-image setters, then "batch" still means:
  - keep the cube open
  - reuse the same projection/camera object
  - iterate over many points without reopening the cube each time
- Do not simulate batching by calling a single-point helper that itself opens and closes the cube for every point.

## Camera-operation guidance

- For repeated image-coordinate -> ground, ground -> image-coordinate, stereo seeding, footprint checks, or similar camera-backed geometry on the same cube, fetch the camera once per opened cube when the API allows it.
- Prefer this structure:
  1. open cube once
  2. fetch `camera = cube.camera()` once
  3. process many coordinate pairs with the same camera object
  4. close cube once after the full batch
- If the camera API is stateful and uses methods such as image-setting or ground-setting calls, batching still means reusing the same camera object across many points instead of reacquiring `cube.camera()` inside the loop.
- When operating on a stereo pair or many cubes, open each cube once per batch and keep the corresponding left/right camera objects alive together for the full paired operation.
- Do not reacquire `cube.camera()` for every point unless you have evidence that a specific upstream lifecycle rule requires it.

## Raster/window guidance

- For repeated reads from the same cube, prefer reusing the opened cube across all requested windows or tiles.
- If a loop reads many windows from one cube, keep `Cube`, `Brick`, manager, or similar reusable state outside the inner loop when practical.
- Avoid per-window reopen patterns unless a real lifecycle limitation forces them.

## Brick guidance

- When repeatedly reading or writing many windows of compatible shape from the same cube, prefer reusing a `Brick` object when practical instead of constructing a fresh `Brick` for every iteration.
- Reuse is especially preferred when:
  - tile width/height/band shape stays constant across the loop
  - only the base position changes between iterations
- Keep the coordinate-basis rule explicit when reusing `Brick`:
  - if Python-side tile/window offsets are 0-based but ISIS `Brick` base positions are 1-based, preserve the `+1` conversion at the point where base position is set
- If window dimensions vary across iterations, recreating the `Brick` may be acceptable; still keep the cube open across the full loop.
- Do not hide repeated per-window `Brick` reconstruction behind a helper if the helper also reopens the cube each time.

## LineManager guidance

- For row-by-row or line-by-line raster traversal, prefer one `LineManager` lifecycle per cube operation, not one manager construction per line.
- Typical preferred flow is:
  1. open cube once
  2. create `LineManager(cube)` once
  3. call `begin()` once
  4. iterate with `next()` / `end()` across all required lines
  5. close cube once
- When writing many lines, keep the line manager alive across the full write loop so the per-line work changes values and position, not manager ownership.
- If only a subset of lines is needed, still prefer one manager object plus position updates instead of reconstructing a new manager for every individual line.

## Exception and diagnostics rule

- Batch-style helpers must preserve enough context for debugging.
- If one point fails, raise an error that still includes:
  - the cube path
  - the failing coordinate pair or point
  - the operation being attempted when useful
- Do not trade away actionable diagnostics just to reduce function-call count.

## Resource-lifecycle rule

- In Python, prefer `try` / `finally` around long-lived opened cubes so cleanup still occurs on the first failing point.
- In C++, prefer local object lifetime / RAII and avoid manual ownership patterns when a stack object or smart pointer can express the lifecycle safely.
- If helper objects returned from a cube depend on the cube's lifetime, keep the cube alive for the full duration of the batch operation.
- Apply the same lifetime rule to cube-derived helpers such as `Projection`, `Camera`, `Brick`, `LineManager`, and similar ISIS managers or mappers whose valid usage depends on the opened cube remaining alive.

## When not to over-apply

- If only one point or one window is processed, a dedicated batch helper is optional.
- If upstream ISIS lifecycle or thread/process boundaries require reopening in separate workers, reopen **per worker**, not per point.
- If an API is stateful and reusing one helper object would corrupt correctness, document that reason explicitly before falling back to repeated construction.

## Preferred review question

Before finishing a change, ask:

- "Am I reopening the same cube or recreating the same projection/camera/Brick/LineManager object inside a point or window loop when I could open once and batch the work instead?"
