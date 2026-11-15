#!/usr/bin/env python3
"""Dragon Gate Leap — make.fun ai-excited-01 entry (Python 3.13, stdlib only).

The entry image is drawn procedurally by generate.py (pure standard
library: a hand-rolled rasteriser over a raw RGB buffer, PNG encoded with
zlib) and written to /output/entry.png. No network, no external assets,
deterministic: two runs write identical bytes.

Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for /output:
  mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
from pathlib import Path

import generate

HERE = Path(__file__).resolve().parent
OUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

OUT_DIR.mkdir(parents=True, exist_ok=True)
size = generate.render(str(OUT_DIR / "entry.png"))
print(f"entry.png: {generate.W}x{generate.H}, {size} bytes")
