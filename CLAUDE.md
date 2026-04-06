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

**Particle Garden** (`particles/index.html`): Single-file p5.js sketch using:
- Two hand-drawn flower PNGs (`particles/flower1.png`, `flower2.png`) rendered with ADD blend mode and HSB tinting
- Particle system (max 120) with noise-based drift, mouse repulsion, bloom animation, trail system (max 2000), and lifecycle/wilting
- Click spawns burst of 5-12 flowers radiating outward

## Key Patterns

- All JavaScript is inline within HTML files (no separate .js files)
- External libraries loaded from CDN only (p5.js 1.9.0, MediaPipe vision 0.10.18)
- Webcam feed is mirrored horizontally (grid renders right-to-left: `COLS - 1 - col`)
- Color treatments in `treatColor()` are indexed by mode number — adding a new mode means adding a case there plus a draw block in `drawNormalMode()`
- Grid cells store persistent per-mode state that resets on mode switch (`doActualModeSwap`)
