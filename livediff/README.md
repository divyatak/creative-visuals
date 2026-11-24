# livediff — stage 0 of the portal experiment

Standalone test: how fast and how stable is live img2img diffusion on this
laptop's RTX 4070? No browser, no portal — webcam in, SD-Turbo out, side by
side in one window.

## Run

```
cd livediff
venv\Scripts\python gen.py
```

First run downloads sd-turbo (~2.5 GB) into the Hugging Face cache
(`%USERPROFILE%\.cache\huggingface`).

## Keys

| key | does |
| --- | --- |
| `[` / `]` | denoising strength down / up — the style-vs-stability dial |
| `p` | next preset prompt |
| `s` | save input+output pair to `captures/` |
| `q` | quit |

## What to look for

- **gen/s** in the overlay: 7+ means the portal's 4–15 FPS target is met.
  Measured headless on this machine: **9.6 gen/s** at 512 (tiny VAE, cached
  prompt embeds), 3.7 with `--full-vae`. Webcam capture will shave a little off.
- **Flicker while holding the camera still**: the seed is fixed, so a static
  scene should produce a near-static output. If it shimmers badly at the
  strength you like, temporal tricks (feedback blend, skip-when-static) are
  the next experiment.
- **Strength sweet spot**: below ~0.35 the style barely shows; above ~0.6
  structure starts melting. The portal wants the widest usable band.

`venv/` and `captures/` are gitignored; only this file and `gen.py` are
tracked.
