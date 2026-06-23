# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A static HTML site hosting interactive visual art experiments. No build system, no bundler, no package manager — just HTML files with inline CSS/JS served directly from a web server or opened in a browser.

## Running

Open any `index.html` in a browser. For webcam features, use a local server (e.g. `npx serve .` or VS Code Live Server) since MediaPipe requires HTTPS/localhost for camera access.

## Architecture

**Landing page** (`index.html`): Card-based nav linking to sub-projects.

**Webcam Magic** (`webcam/index.html`): Single-file app (~710 lines) combining:
- **p5.js** (CDN) for canvas rendering
- **MediaPipe HandLandmarker** (CDN, ES module import) for real-time hand tracking
- A 100x75 pixel grid (`COLS`/`ROWS`) where each cell has physics state (position, velocity, per-mode properties like `erased`, `painted`, `dotScale`, etc.)
- 7 visual modes (`MODE_NAMES` array): Duotone Ripple, Shifted Erase, Thermal Paint, Halftone Sculpt, ASCII Smear, Mosaic Sharpen, Static Calm
- Mode switching via peace sign gesture (1.5s hold) or mouse click; transitions use a 5-frame RGB-tear glitch effect
- Dual resolution: low-res grid (`camPx`, 100x75) for per-cell color + high-res (`hiResPx`, 640x480) for Mosaic Sharpen's detail reveal
- Finger speed controls effect radius (`getRadius()`): faster = larger radius
- Mouse wheel controls `intensity` (0.3-3.0) scaling effect strength

**Bioluminescent Flow** (`particles/index.html`): Single-file three.js GPGPU sketch (titled "BIOLUMINESCENT FLOW" on the landing page). ~25k glowing algae particles simulated entirely on the GPU.
- **three.js 0.170** + `GPUComputationRenderer` (CDN); **MediaPipe HandLandmarker** (CDN) for hand tracking, mouse as fallback
- Particle state lives in two float textures (`texPos` = position+velocity, `texData` = age/maxAge/excitation/hue), ping-ponged each frame — no per-particle CPU loop
- **Motion** (`posFrag`): one shared **laminar current** (a breathing direction split into meandering, thick/thin *laminae* via a cross-stream speed profile) + a small per-particle curl-noise wander + shimmer jitter
- Hands are rendered as a glowing **SDF silhouette** (`genSDFBody` builds the GLSL from finger/palm landmarks); particles repel from the SDF edge and brighten where they crowd (additive blend)
- Trails via a ping-pong feedback buffer (`fadeMat` fades the previous frame)

**Tuning the bioluminescent sim:**
- All tunable values live in the `DEFAULTS` object (fallback) but the real source of truth is **`particles/defaults.json`**, which the page fetches at startup and which overrides `DEFAULTS`. To change the look that ships, edit/commit that JSON — no code edit needed.
- Append **`?tune`** to the URL **on localhost only** (`localhost:3000/particles/?tune`) to mount live slider panels (flow + particles). The deployed site can never show the tuner (gated on `IS_LOCAL`).
- Every slider change is auto-saved: it POSTs (debounced) to `/__tune`, which **`tune-server.cjs`** writes straight into `particles/defaults.json`. So tuned values are "saved" the instant you drag — committing + pushing that file ships them live.
- **Run `node tune-server.cjs`** (serves on :3000) instead of `npx serve` when a tuning session is needed; it's the static server *plus* the `/__tune` write endpoint.

## Key Patterns

- All JavaScript is inline within HTML files (no separate .js files)
- External libraries loaded from CDN only (p5.js 1.9.0, MediaPipe vision 0.10.18)
- Webcam feed is mirrored horizontally (grid renders right-to-left: `COLS - 1 - col`)
- Color treatments in `treatColor()` are indexed by mode number — adding a new mode means adding a case there plus a draw block in `drawNormalMode()`
- Grid cells store persistent per-mode state that resets on mode switch (`doActualModeSwap`)
