#!/usr/bin/env python3
"""CLI for generating or editing images with OpenAI gpt-image-2.

Examples:
  python gpt_image_2_cli.py generate \
    --api-key YOUR_OPENAI_API_KEY \
    --prompt "A realistic studio photo of a ceramic mug" \
    --output mug.png

  python gpt_image_2_cli.py edit \
    --api-key YOUR_OPENAI_API_KEY \
    --prompt "Turn this into a watercolor illustration" \
    --image input.png \
    --output edited.png
"""

from __future__ import annotations

import argparse
import base64
import getpass
import os
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Iterable, List

from openai import OpenAI

VALID_FORMATS = {"png", "jpeg", "webp"}
VALID_QUALITIES = {"low", "medium", "high", "auto"}
VALID_BACKGROUNDS = {"transparent", "opaque", "auto"}


def fail(message: str, exit_code: int = 2) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or edit images with OpenAI gpt-image-2 via the Image API."
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key. If omitted, the script prompts securely.",
    )
    parser.add_argument(
        "--model",
        default="gpt-image-2",
        help="Image model to use. Defaults to gpt-image-2.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--prompt", required=True, help="Prompt sent to the image model.")
        subparser.add_argument("--size", help="Output size, e.g. 1024x1024 or 1536x1024.")
        subparser.add_argument(
            "--quality",
            choices=sorted(VALID_QUALITIES),
            help="Rendering quality. Supported values: low, medium, high, auto.",
        )
        subparser.add_argument(
            "--output-format",
            choices=sorted(VALID_FORMATS),
            help="Output format returned by the API: png, jpeg, or webp.",
        )
        subparser.add_argument(
            "--output-compression",
            type=int,
            help="Compression level 0-100 for jpeg/webp outputs.",
        )
        subparser.add_argument(
            "--background",
            choices=sorted(VALID_BACKGROUNDS),
            help="Background mode: transparent, opaque, or auto.",
        )
        subparser.add_argument(
            "--n",
            type=int,
            default=1,
            help="Number of images to create. Defaults to 1.",
        )
        subparser.add_argument(
            "--output",
            help="Single output file path. Only valid when exactly one image is returned.",
        )
        subparser.add_argument(
            "--output-dir",
            default=".",
            help="Directory for generated files when --output is omitted or when n > 1.",
        )
        subparser.add_argument(
            "--prefix",
            default="image",
            help="Filename prefix used for auto-generated output names.",
        )

    generate = subparsers.add_parser("generate", help="Generate new image(s) from text.")
    add_common(generate)

    edit = subparsers.add_parser("edit", help="Edit one or more input images.")
    add_common(edit)
    edit.add_argument(
        "--image",
        action="append",
        required=True,
        help="Input image path. Repeat to send multiple reference images.",
    )
    edit.add_argument(
        "--mask",
        help="Optional mask PNG path for inpainting. Transparent areas indicate editable regions.",
    )
    edit.add_argument(
        "--input-fidelity",
        choices=["low", "high"],
        help="For supported models, control how closely edits should match source image details.",
    )

    return parser.parse_args()


def infer_output_format(args: argparse.Namespace) -> str:
    if args.output_format:
        return args.output_format
    if args.output:
        suffix = Path(args.output).suffix.lower().lstrip(".")
        if suffix == "jpg":
            return "jpeg"
        if suffix in VALID_FORMATS:
            return suffix
    return "png"


def validate_args(args: argparse.Namespace) -> None:
    if args.n < 1:
        fail("--n must be at least 1.")
    if args.output_compression is not None and not (0 <= args.output_compression <= 100):
        fail("--output-compression must be between 0 and 100.")
    if args.output and args.n != 1:
        fail("--output can only be used when --n is 1. Use --output-dir for multiple images.")
    if args.background == "transparent" and args.model.startswith("gpt-image-2"):
        fail("gpt-image-2 does not currently support transparent backgrounds. Use opaque or auto.")
    if args.command == "edit" and args.mask:
        mask_path = Path(args.mask)
        if not mask_path.exists():
            fail(f"Mask file not found: {mask_path}")
    if args.command == "edit":
        for image_path in args.image:
            if not Path(image_path).exists():
                fail(f"Input image not found: {image_path}")
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)


def resolve_api_key(raw_api_key: str | None) -> str:
    api_key = raw_api_key or getpass.getpass("OpenAI API key: ")
    if not api_key:
        fail("Missing API key. Pass --api-key or enter one when prompted.")
    return api_key


def build_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def collect_generate_kwargs(args: argparse.Namespace) -> dict:
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "n": args.n,
        "output_format": infer_output_format(args),
    }
    if args.size:
        payload["size"] = args.size
    if args.quality:
        payload["quality"] = args.quality
    if args.output_compression is not None:
        payload["output_compression"] = args.output_compression
    if args.background:
        payload["background"] = args.background
    return payload


def collect_edit_kwargs(args: argparse.Namespace, stack: ExitStack) -> dict:
    images: List[object] = []
    for image_path in args.image:
        images.append(stack.enter_context(open(image_path, "rb")))

    payload = {
        "model": args.model,
        "image": images if len(images) > 1 else images[0],
        "prompt": args.prompt,
        "n": args.n,
        "output_format": infer_output_format(args),
    }
    if args.size:
        payload["size"] = args.size
    if args.quality:
        payload["quality"] = args.quality
    if args.output_compression is not None:
        payload["output_compression"] = args.output_compression
    if args.background:
        payload["background"] = args.background
    if args.input_fidelity:
        payload["input_fidelity"] = args.input_fidelity
    if args.mask:
        payload["mask"] = stack.enter_context(open(args.mask, "rb"))
    return payload


def output_extension(output_format: str) -> str:
    return "jpg" if output_format == "jpeg" else output_format


def save_images(images: Iterable[object], args: argparse.Namespace, chosen_format: str) -> List[Path]:
    decoded = []
    for image in images:
        b64 = getattr(image, "b64_json", None)
        if not b64:
            fail("API response did not include b64_json image data.")
        decoded.append(base64.b64decode(b64))

    if not decoded:
        fail("No images were returned by the API.")

    saved_paths: List[Path] = []
    if args.output:
        if len(decoded) != 1:
            fail("--output requires exactly one generated image.")
        output_path = Path(args.output)
        output_path.write_bytes(decoded[0])
        saved_paths.append(output_path)
        return saved_paths

    ext = output_extension(chosen_format)
    base_dir = Path(args.output_dir)
    for index, blob in enumerate(decoded, start=1):
        filename = f"{args.prefix}_{index:03d}.{ext}"
        path = base_dir / filename
        path.write_bytes(blob)
        saved_paths.append(path)
    return saved_paths


def maybe_print_revised_prompts(images: Iterable[object]) -> None:
    printed = False
    for idx, image in enumerate(images, start=1):
        revised = getattr(image, "revised_prompt", None)
        if revised:
            if not printed:
                print("Revised prompt(s):")
                printed = True
            print(f"  [{idx}] {revised}")


def main() -> None:
    args = parse_args()
    validate_args(args)
    api_key = resolve_api_key(args.api_key)
    client = build_client(api_key)
    chosen_format = infer_output_format(args)

    if args.command == "generate":
        result = client.images.generate(**collect_generate_kwargs(args))
    else:
        with ExitStack() as stack:
            result = client.images.edit(**collect_edit_kwargs(args, stack))

    images = list(result.data or [])
    saved_paths = save_images(images, args, chosen_format)

    print("Saved image(s):")
    for path in saved_paths:
        print(f"  {path}")
    maybe_print_revised_prompts(images)


if __name__ == "__main__":
    main()
