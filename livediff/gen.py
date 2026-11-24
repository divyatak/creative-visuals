# livediff/gen.py -- Stage 0 of the portal experiment.
# Webcam -> SD-Turbo img2img -> window, in a loop. No browser, no portal:
# this only answers "how fast and how stable is live diffusion on this GPU?"
#
# Run:  venv\Scripts\python gen.py            (512x512, tiny VAE)
#       venv\Scripts\python gen.py --size 384 (faster)
#       venv\Scripts\python gen.py --full-vae (slower, best decode quality)
# Keys: [ / ]  = denoising strength down/up (the style-vs-stability dial)
#       p      = next preset prompt
#       s      = save input+output pair into captures/
#       q      = quit

import argparse
import math
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from diffusers import AutoencoderTiny, AutoPipelineForImage2Image
from PIL import Image

SEED = 42           # fixed noise across frames -- pillar #1 of temporal stability
CAMERA_INDEX = 0

PROMPTS = [
    "an overgrown room reclaimed by jungle plants, vines and moss, soft light",
    "the same room underwater, caustic light, drifting particles, teal depths",
    "a watercolor illustration of a room, loose ink lines, paper texture",
    "a futuristic neon cyberpunk interior, holographic surfaces, night",
    "a room inside a paper diorama, cut cardboard layers, handmade",
]


def load_pipe(full_vae):
    pipe = AutoPipelineForImage2Image.from_pretrained(
        "stabilityai/sd-turbo", torch_dtype=torch.float16, variant="fp16"
    )
    pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)
    if not full_vae:
        # distilled VAE: decode drops from ~100ms to ~10ms for a small quality cost
        pipe.vae = AutoencoderTiny.from_pretrained(
            "madebyollin/taesd", torch_dtype=torch.float16
        ).to("cuda")
    return pipe


def center_crop_square(frame):
    h, w = frame.shape[:2]
    s = min(h, w)
    y, x = (h - s) // 2, (w - s) // 2
    return frame[y : y + s, x : x + s]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=512, help="model-facing resolution")
    ap.add_argument("--full-vae", action="store_true", help="use the full VAE decoder")
    args = ap.parse_args()
    size = args.size

    print("loading sd-turbo...")
    pipe = load_pipe(args.full_vae)
    # the prompt is encoded once per prompt-switch, never per frame
    embed_cache = {}
    def embeds_for(i):
        if i not in embed_cache:
            embed_cache[i] = pipe.encode_prompt(PROMPTS[i], "cuda", 1, False)[0]
        return embed_cache[i]
    print("pipeline ready.")

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise SystemExit("no webcam found on index %d" % CAMERA_INDEX)

    strength = 0.45
    prompt_i = 0
    captures = Path(__file__).parent / "captures"
    fps = 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)  # mirror, like every station on the site
        square = cv2.resize(center_crop_square(frame), (size, size))
        src = Image.fromarray(cv2.cvtColor(square, cv2.COLOR_BGR2RGB))

        # turbo needs int(steps * strength) >= 1; keep the *effective* steps at 1
        steps = max(1, math.ceil(1.0 / strength))
        t0 = time.perf_counter()
        out = pipe(
            prompt_embeds=embeds_for(prompt_i),
            image=src,
            num_inference_steps=steps,
            strength=strength,
            guidance_scale=0.0,
            generator=torch.Generator("cuda").manual_seed(SEED),
        ).images[0]
        dt = time.perf_counter() - t0
        fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps else 1.0 / dt

        out_bgr = cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)
        panel = np.hstack([square, out_bgr])
        label = "%.1f gen/s   strength %.2f   [%d/%d] %s" % (
            fps, strength, prompt_i + 1, len(PROMPTS), PROMPTS[prompt_i][:52],
        )
        cv2.putText(panel, label, (10, size - 14), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(panel, label, (10, size - 14), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow("livediff -- q quit, [ ] strength, p prompt, s save", panel)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("["):
            strength = max(0.15, round(strength - 0.05, 2))
        elif key == ord("]"):
            strength = min(0.95, round(strength + 0.05, 2))
        elif key == ord("p"):
            prompt_i = (prompt_i + 1) % len(PROMPTS)
        elif key == ord("s"):
            captures.mkdir(exist_ok=True)
            stamp = time.strftime("%H%M%S")
            cv2.imwrite(str(captures / ("%s_in.png" % stamp)), square)
            cv2.imwrite(str(captures / ("%s_out.png" % stamp)), out_bgr)
            print("saved pair", stamp)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
