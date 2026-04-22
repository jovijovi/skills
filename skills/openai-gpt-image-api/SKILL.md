---
name: openai-gpt-image-api
description: Use OpenAI GPT Image models (especially gpt-image-2) for image generation and editing via the Image API, with guidance on when not to use the Responses image_generation tool.
version: 1.1.0
author: jovijovi
website: https://github.com/jovijovi/skills
license: MIT
---

# OpenAI GPT Image API

Use this skill when the user asks how to call OpenAI's GPT image models directly, especially `gpt-image-2`.

## Key rule

If the user wants to **explicitly select `gpt-image-2`**, use the **Image API**:
- `POST /v1/images/generations`
- SDK: `client.images.generate(...)`

Do **not** recommend the Responses API image tool for explicit model pinning. The docs note that the Responses API `image_generation` tool uses its own GPT Image model selection, so it is better for conversational workflows than for guaranteed direct selection of `gpt-image-2`.

## When to use which API

### Use Image API when:
- Single-turn text-to-image generation
- Single-turn image edit / inpainting
- The caller wants to explicitly set `model="gpt-image-2"`
- The caller wants direct control of size / quality / format / compression

### Use Responses API when:
- Multi-turn image editing inside a conversation
- You want the main model to decide when to generate vs edit
- You want to pass image File IDs in conversational context

## Core model facts

From OpenAI docs:
- Latest GPT image model: `gpt-image-2`
- Snapshot example: `gpt-image-2-2026-04-21`
- Image endpoints include:
  - `/v1/images/generations`
  - `/v1/images/edits`
- Responses tool type: `image_generation`
- Organization verification may be required before using GPT Image models

## Quick Start CLI script

This skill now includes a runnable Python CLI script:
- `scripts/gpt_image_2_cli.py`

Use it for either generation or editing.

### Generate an image

```bash
python ~/.hermes/skills/mlops/openai-gpt-image-api/scripts/gpt_image_2_cli.py generate \
  --api-key YOUR_OPENAI_API_KEY \
  --prompt "A realistic photo of a small kitten sitting by a window, warm morning light" \
  --output kitten.png
```

### Edit an image

```bash
python ~/.hermes/skills/mlops/openai-gpt-image-api/scripts/gpt_image_2_cli.py edit \
  --api-key YOUR_OPENAI_API_KEY \
  --prompt "Turn this into a cinematic watercolor illustration" \
  --image input.png \
  --output edited.png
```

### Inpaint with a mask

```bash
python ~/.hermes/skills/mlops/openai-gpt-image-api/scripts/gpt_image_2_cli.py edit \
  --api-key YOUR_OPENAI_API_KEY \
  --prompt "Replace the masked area with a red ceramic mug" \
  --image desk.png \
  --mask mask.png \
  --output inpainted.png
```

The script accepts `--api-key` directly and, if omitted, prompts securely for the key at runtime.

## Minimal Python example

```python
from openai import OpenAI
import base64

client = OpenAI()

result = client.images.generate(
    model="gpt-image-2",
    prompt="A realistic photo of a small kitten sitting by a window, warm morning light",
)

with open("kitten.png", "wb") as f:
    f.write(base64.b64decode(result.data[0].b64_json))
```

## Minimal Node.js example

```javascript
import OpenAI from "openai";
import fs from "fs";

const openai = new OpenAI();

const result = await openai.images.generate({
  model: "gpt-image-2",
  prompt: "A realistic photo of a small kitten sitting by a window, warm morning light"
});

fs.writeFileSync("kitten.png", Buffer.from(result.data[0].b64_json, "base64"));
```

## Minimal curl example

```bash
curl -X POST "https://api.openai.com/v1/images/generations" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "A realistic photo of a small kitten sitting by a window, warm morning light"
  }' | jq -r '.data[0].b64_json' | base64 --decode > kitten.png
```

## Output handling

GPT Image responses from the Image API return base64 image data in:
- `result.data[0].b64_json`

Decode it before saving.

## Useful parameters

```python
result = client.images.generate(
    model="gpt-image-2",
    prompt="A ceramic teacup on a wooden table, studio product photo",
    size="1536x1024",
    quality="high",
    output_format="jpeg",
    output_compression=80,
    background="auto",
)
```

Common parameters:
- `model`
- `prompt`
- `size`
- `quality`
- `output_format` = `png` | `jpeg` | `webp`
- `output_compression` = 0..100 for jpeg/webp
- `background` = `opaque` | `auto`
- `n` for multiple images

## gpt-image-2 size constraints

Docs note:
- Max edge length: `<= 3840`
- Both dimensions must be multiples of `16`
- Long edge / short edge ratio must not exceed `3:1`
- Total pixels must be between `655,360` and `8,294,400`

Common sizes:
- `1024x1024`
- `1536x1024`
- `1024x1536`
- `2048x2048`
- `2048x1152`
- `3840x2160`
- `2160x3840`
- `auto`

Square images are typically fastest.

## Quality guidance

- `low`: drafts, quick iterations, thumbnails
- `medium`: balanced default for many cases
- `high`: final assets
- `auto`: let model choose

## Important limitations / pitfalls

### Transparent background
`gpt-image-2` does **not** currently support `background="transparent"`.
Use:
- `background="opaque"`, or
- `background="auto"`

### Latency
Complex prompts can take up to ~2 minutes.

### Text rendering and layout
Still improved but not perfect:
- precise text placement can fail
- strict layout-sensitive compositions may drift
- visual consistency across repeated character generations may vary

### Responses API caveat
In Responses API, this is valid:

```python
response = client.responses.create(
    model="gpt-5.4",
    input="Generate an image of a gray tabby cat hugging an otter",
    tools=[{"type": "image_generation"}],
)
```

But use this for conversational workflows, not when the user specifically asks to directly call `gpt-image-2`.

## Verification checklist

Before finalizing advice, confirm:
1. If the user wants explicit `gpt-image-2` selection, recommend Image API.
2. Mention base64 decoding.
3. Mention transparent background is unsupported on `gpt-image-2`.
4. Mention size constraints if discussing custom resolutions.
5. Mention org verification may be required if access issues arise.
6. If the user wants runnable code, prefer the bundled `scripts/gpt_image_2_cli.py` script and show the exact command.

## Bundled script behavior

`scripts/gpt_image_2_cli.py` supports:
- `generate` subcommand for text-to-image
- `edit` subcommand for image editing or reference-based generation
- multiple `--image` inputs for edit mode
- optional `--mask` for inpainting
- `--size`, `--quality`, `--output-format`, `--output-compression`, `--background`, and `--n`
- `--output` for a single file or `--output-dir` for multiple outputs
- default model `gpt-image-2`

If `--output` is omitted, the script writes numbered files into the current directory.
