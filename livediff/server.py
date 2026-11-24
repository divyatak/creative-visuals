# livediff/server.py -- the portal's stylization half.
# WebSocket loop: receive a JPEG of the full video frame, return it anime-fied.
# The browser sends in lockstep (next frame only after the last reply),
# so there is no queue to manage and stale frames are never processed.
#
# Three engines:
#   anime (default) -- Anything-v5 + Hyper-SD 1-step + ControlNet(canny).
#                      Structure is pinned by the edge map, so strength runs
#                      HIGH (0.9-1.0): the model repaints in full anime style
#                      while the edges keep it your scene. ~150ms/frame.
#   animegan        -- feed-forward GAN, fast + deterministic, dated look.
#   turbo           -- sd-turbo img2img, promptable generic worlds, mushy.
#
# The portal page can retune live: it sends {"strength": x} as a JSON text
# message on the same socket ([ and ] keys); binary messages are frames.
#
# Run:  venv\Scripts\python server.py
#       venv\Scripts\python server.py --strength 0.95 --cscale 0.7
#       venv\Scripts\python server.py --engine turbo --prompt "underwater room..."

import argparse
import asyncio
import io
import json
import math

import cv2
import numpy as np
import torch
import websockets
from PIL import Image

SEED = 42

DEFAULT_PROMPT = (
    "masterpiece, best quality, anime screencap, clean bold lineart, "
    "cel shading, vibrant colors, glossy lighting, detailed"
)

# bryandlee/animegan2-pytorch pretrained weights:
#   face_paint_512_v2 -- cleanest "shiny" portrait look (best when you're in frame)
#   paprika           -- scene stylization, painterly
#   celeba_distill / face_paint_512_v1 -- older variants
def load_animegan(style):
    model = torch.hub.load("bryandlee/animegan2-pytorch:main", "generator",
                           pretrained=style, trust_repo=True)
    model.eval().half().to("cuda")

    @torch.no_grad()
    def generate(img):
        t = torch.from_numpy(np.asarray(img)).to("cuda").half()
        t = t.permute(2, 0, 1).unsqueeze(0) / 127.5 - 1.0
        out = model(t)[0].clamp(-1, 1)
        arr = ((out.permute(1, 2, 0) + 1.0) * 127.5).byte().cpu().numpy()
        return Image.fromarray(arr)

    return generate


def _finish_pipe(pipe, full_vae):
    from diffusers import AutoencoderTiny

    pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)
    if not full_vae:
        pipe.vae = AutoencoderTiny.from_pretrained(
            "madebyollin/taesd", torch_dtype=torch.float16
        ).to("cuda")
    return pipe


def _img2img(pipe, embeds, strength, extra=None):
    steps = max(1, math.ceil(1.0 / strength))

    def generate(img):
        kwargs = dict(
            prompt_embeds=embeds,
            image=img,
            num_inference_steps=steps,
            strength=strength,
            guidance_scale=0.0,
            generator=torch.Generator("cuda").manual_seed(SEED),
        )
        if extra:
            kwargs.update(extra)
        return pipe(**kwargs).images[0]

    return generate


def load_anime(prompt, state, full_vae):
    from diffusers import (ControlNetModel,
                           StableDiffusionControlNetImg2ImgPipeline,
                           TCDScheduler)

    controlnet = ControlNetModel.from_pretrained(
        "lllyasviel/control_v11p_sd15_canny", torch_dtype=torch.float16
    )
    pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
        "stablediffusionapi/anything-v5", controlnet=controlnet,
        torch_dtype=torch.float16, safety_checker=None
    )
    pipe = _finish_pipe(pipe, full_vae)
    pipe.load_lora_weights("ByteDance/Hyper-SD",
                           weight_name="Hyper-SD15-1step-lora.safetensors")
    pipe.fuse_lora()
    pipe.scheduler = TCDScheduler.from_config(pipe.scheduler.config)
    embeds = pipe.encode_prompt(prompt, "cuda", 1, False)[0]

    def generate(img):
        # blur before canny so webcam sensor noise doesn't fragment the lines
        arr = np.asarray(img)
        e = cv2.Canny(cv2.GaussianBlur(arr, (5, 5), 0), 80, 160)
        cn = Image.fromarray(np.stack([e] * 3, axis=-1))
        s = state["strength"]
        return pipe(
            prompt_embeds=embeds,
            image=img,
            control_image=cn,
            num_inference_steps=max(1, math.ceil(1.0 / s)),
            strength=s,
            guidance_scale=0.0,
            controlnet_conditioning_scale=state["cscale"],
            generator=torch.Generator("cuda").manual_seed(SEED),
        ).images[0]

    return generate


def load_turbo(prompt, strength, full_vae):
    from diffusers import AutoPipelineForImage2Image

    pipe = AutoPipelineForImage2Image.from_pretrained(
        "stabilityai/sd-turbo", torch_dtype=torch.float16, variant="fp16"
    )
    pipe = _finish_pipe(pipe, full_vae)
    embeds = pipe.encode_prompt(prompt, "cuda", 1, False)[0]
    return _img2img(pipe, embeds, strength)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["anime", "animegan", "turbo"],
                    default="anime")
    ap.add_argument("--style", default="face_paint_512_v2",
                    help="animegan style (face_paint_512_v2, paprika, ...)")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT, help="anime/turbo only")
    ap.add_argument("--strength", type=float, default=0.95, help="anime/turbo only")
    ap.add_argument("--cscale", type=float, default=0.8,
                    help="anime only: how hard edges pin the structure")
    ap.add_argument("--full-vae", action="store_true", help="anime/turbo only")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    state = {"strength": args.strength, "cscale": args.cscale}

    print("loading %s..." % args.engine, flush=True)
    if args.engine == "animegan":
        generate = load_animegan(args.style)
        detail = "style " + args.style
    elif args.engine == "anime":
        generate = load_anime(args.prompt, state, args.full_vae)
        detail = "strength %.2f, cscale %.2f" % (args.strength, args.cscale)
    else:
        generate = load_turbo(args.prompt, args.strength, args.full_vae)
        detail = "strength %.2f, prompt: %s" % (args.strength, args.prompt)

    # warm the kernels so the portal's first frame isn't the slow one
    generate(Image.new("RGB", (512, 384), (90, 90, 90)))
    print("pipeline ready (%s, %s)" % (args.engine, detail), flush=True)

    async def handle(ws):
        print("portal connected", flush=True)
        try:
            async for msg in ws:
                if isinstance(msg, (bytes, bytearray)):
                    img = Image.open(io.BytesIO(msg)).convert("RGB")
                    out = generate(img)
                    buf = io.BytesIO()
                    out.save(buf, "JPEG", quality=92)
                    await ws.send(buf.getvalue())
                else:
                    # text = live config from the page: {"strength": 0.9, ...}
                    try:
                        cfg = json.loads(msg)
                        for k in ("strength", "cscale"):
                            if k in cfg:
                                state[k] = float(cfg[k])
                        state["strength"] = min(1.0, max(0.15, state["strength"]))
                        await ws.send(json.dumps(state))
                    except (ValueError, TypeError):
                        pass
        finally:
            print("portal disconnected", flush=True)

    async with websockets.serve(handle, "localhost", args.port,
                                max_size=8 * 1024 * 1024):
        print("listening on ws://localhost:%d" % args.port, flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
