#!/usr/bin/env python3
"""Regenerate assets/banner.svg — the terminal-style header of the profile README.

Pulls the GitHub avatar, traces the subject out of the background, renders it as
an ASCII silhouette, and composes the whole terminal window as one SVG.

    pip install pillow numpy
    python3 assets/make-banner.py

Every glyph of the ASCII art carries its own absolute x, so the grid holds even
when a browser substitutes a non-monospace font.
"""

import os
import urllib.request
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
AVATAR_URL = "https://github.com/abdallah-shehawey.png?size=460"
AVATAR = os.path.join(HERE, ".avatar-cache.png")
OUT = os.path.join(HERE, "banner.svg")

# --------------------------------------------------------------------- art
# Ramp ordered by measured ink coverage of each glyph in a monospace face.
RAMP = " `.'~!;/=|ltsnXaw8mMQB@$"
COLS, ROWS = 56, 56
CROP = (112, 18, 252, 205)         # head and shoulders in the 460x460 avatar

# Subject outline, traced by hand in avatar pixels. Everything outside is
# dropped, which is what keeps the busy photo background out of the ASCII.
FIGURE = [
    (150, 28), (180, 23), (212, 33), (220, 58), (219, 92), (209, 110), (201, 124),
    (228, 130), (252, 146), (264, 170), (273, 205), (282, 245), (293, 280),
    (304, 300), (300, 313), (280, 319), (256, 323), (230, 331), (214, 341),
    (199, 346), (225, 353), (229, 373), (222, 393), (200, 405), (170, 401),
    (159, 379), (150, 361), (139, 373), (150, 396), (168, 416), (171, 441),
    (155, 456), (125, 456), (114, 438), (112, 415), (104, 390), (92, 360),
    (83, 330), (80, 300), (82, 255), (85, 215), (88, 180), (96, 152),
    (112, 138), (140, 126), (167, 122), (173, 111), (157, 104), (146, 87),
    (145, 57),
]

FEATHER, BLUR, GAMMA = 3, 0.25, 1.0
L_SIGMA, L_STRENGTH, L_MIX = 0.10, 2.5, 0.85
P_LO, P_HI, CUT = 1, 99, 0.03


def ascii_portrait():
    if not os.path.exists(AVATAR):
        urllib.request.urlretrieve(AVATAR_URL, AVATAR)
    rgb = Image.open(AVATAR).convert("RGB")

    mask = Image.new("L", rgb.size, 0)
    ImageDraw.Draw(mask).polygon(FIGURE, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(FEATHER)).crop(CROP)

    gray = rgb.convert("L").crop(CROP).filter(ImageFilter.GaussianBlur(BLUR))

    g = np.asarray(gray, np.float32) / 255.0

    # Local contrast: subtract a heavily blurred copy so the lit face and the
    # near-black suit each get the whole ramp instead of sharing one range.
    # Without this the face flattens into blank space and stops being a face.
    sigma = L_SIGMA * (CROP[2] - CROP[0])
    lp = np.asarray(Image.fromarray((g * 255).astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(sigma)), np.float32) / 255.0
    flat = np.clip(0.5 + L_STRENGTH * (g - lp), 0, 1)
    tone = np.clip(L_MIX * flat + (1 - L_MIX) * g, 0, 1)

    def cells(a):
        return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
                          .resize((COLS, ROWS), Image.LANCZOS), np.float32) / 255.0

    t, m = cells(tone), cells(np.asarray(mask, np.float32) / 255.0)

    inside = t[m > 0.5]
    lo, hi = np.percentile(inside, P_LO), np.percentile(inside, P_HI)
    t = np.clip((t - lo) / max(hi - lo, 1e-6), 0, 1)

    dens = np.clip(1.0 - t, 0, 1) ** GAMMA * m
    dens[dens < CUT] = 0.0
    idx = (dens * (len(RAMP) - 1)).round().astype(int)
    return ["".join(RAMP[i] for i in row) for row in idx]


# ------------------------------------------------------------------ layout
W, H = 900, 520
TITLE_H, FOOT_Y = 32, 480
AX, AY, AW, AH = 26.0, 76.0, 280.0, 384.0     # art box, portrait orientation
KX, LX0, LX1, VX, LINE = 356, 440, 492, 500, 18.0

MONO = ("ui-monospace,'SF Mono','JetBrains Mono','Fira Code',"
        "'DejaVu Sans Mono',Menlo,Consolas,monospace")

C = dict(shell="#070b10", win="#0b1017", edge="#182231", bar="#0c131c",
         panel="#090e14", panel_edge="#16202c", label="#3b4b5f", key="#58a6ff",
         val="#c5d2e0", dim="#5b6b80", rule="#1d2937", sec="#7ee787",
         live="#3fb950", foot="#31435a", tag="#46586e")

INFO = [
    ("head", "abdallah@embedded", None),
    ("kv", "Name:", "Abdallah Shehawey"),
    ("kv", "Role:", "Embedded Software Engineer"),
    ("kv", "Based:", "El Mahalla El Kubra, Gharbia, Egypt"),
    ("kv", "Mode:", "Bare-Metal / RTOS / Automotive"),
    ("gap", None, None),
    ("sec", "BUILD.FOCUS", None),
    ("kv", "MCU:", "ARM Cortex-M, AVR, PIC"),
    ("kv", "RTOS:", "FreeRTOS, scheduling, IPC"),
    ("kv", "Vehicle:", "AUTOSAR, CAN, V2X safety"),
    ("kv", "Linux:", "Yocto, drivers, Raspberry Pi"),
    ("gap", None, None),
    ("sec", "ONLINE", None),
    ("kv", "Site:", "abdallahshehawey.vercel.app"),
    ("kv", "Blog:", "shinux.vercel.app"),
    ("kv", "LinkedIn:", "in/abdallah-shehawey"),
    ("kv", "GitHub:", "@abdallah-shehawey"),
    ("gap", None, None),
    ("tag", "FROM DATASHEET TO WORKING HARDWARE", None),
]

FOOTER = "EMBEDDED SYSTEMS  /  AUTOMOTIVE  /  RTOS &amp; AUTOSAR  /  EMBEDDED LINUX"


def art_svg(art):
    cw, ch = AW / COLS, AH / ROWS
    xs = [round(AX + i * cw, 2) for i in range(COLS)]
    out = []
    for r, line in enumerate(art):
        glyphs = [(i, c) for i, c in enumerate(line) if c != " "]
        if not glyphs:
            continue
        pos = " ".join(f"{xs[i]:g}" for i, _ in glyphs)
        y = round(AY + (r + 0.82) * ch, 2)
        out.append(f'<text x="{pos}" y="{y:g}">'
                   f'{escape("".join(c for _, c in glyphs))}</text>')
    return "\n      ".join(out), round(ch * 0.94, 2)


def info_svg():
    out, y = [], 98.0
    for kind, a, b in INFO:
        if kind == "gap":
            y += LINE * 0.8
            continue
        if kind == "head":
            out.append(f'<text class="hd" x="{KX-10}" y="{y:g}">{escape(a)}</text>')
            out.append(f'<line class="rl" x1="{KX+134}" y1="{y-4:g}" x2="874" y2="{y-4:g}"/>')
        elif kind == "tag":
            out.append(f'<text class="tg" x="{KX-10}" y="{y+6:g}">{escape(a)}</text>')
        elif kind == "sec":
            out.append(f'<text class="sc" x="{KX-10}" y="{y:g}">- {escape(a)}</text>')
            out.append(f'<line class="rl" x1="{KX+32+len(a)*7.6:g}" y1="{y-4:g}" '
                       f'x2="874" y2="{y-4:g}"/>')
        else:
            out.append(f'<text class="k" x="{KX}" y="{y:g}">{escape(a)}</text>')
            out.append(f'<line class="ld" x1="{LX0}" y1="{y-3:g}" x2="{LX1}" y2="{y-3:g}"/>')
            out.append(f'<text class="v" x="{VX}" y="{y:g}">{escape(b)}</text>')
        y += LINE
    return "\n      ".join(out)


def main():
    ART, FS = art_svg(ascii_portrait())
    BODY = info_svg()

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img"
     aria-label="Abdallah Shehawey - Embedded Software Engineer">
  <title>Abdallah Shehawey - Embedded Software Engineer</title>

  <defs>
    <linearGradient id="ink" x1="0" y1="0" x2="0.25" y2="1">
      <stop offset="0"    stop-color="#b9d4ff"/>
      <stop offset="0.35" stop-color="#6ea8fe"/>
      <stop offset="0.75" stop-color="#3878cf"/>
      <stop offset="1"    stop-color="#1f4f8f"/>
    </linearGradient>
    <linearGradient id="glow" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1e60c8" stop-opacity="0.16"/>
      <stop offset="1" stop-color="#1e60c8" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="win"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="12"/></clipPath>
  </defs>

  <style>
    text {{ font-family: {MONO}; white-space: pre; }}
    .bar  {{ font-size: 10.5px; fill: {C['dim']}; }}
    .lbl  {{ font-size: 8.5px;  fill: {C['label']}; letter-spacing: 1.5px; }}
    .art  {{ font-size: {FS}px; fill: url(#ink); }}
    .hd   {{ font-size: 12px;   fill: #e6edf6; font-weight: 600; }}
    .sc   {{ font-size: 10.5px;   fill: {C['sec']}; letter-spacing: 0.6px; }}
    .k    {{ font-size: 12px; fill: {C['key']}; }}
    .v    {{ font-size: 12px; fill: {C['val']}; }}
    .rl   {{ stroke: {C['rule']}; stroke-width: 1; }}
    .ld   {{ stroke: #2b3a4d; stroke-width: 1; stroke-dasharray: 1.5 3.5;
             stroke-linecap: round; }}
    .foot {{ font-size: 9px; fill: {C['foot']}; letter-spacing: 2.2px; }}
    .live {{ font-size: 9px; fill: {C['live']}; letter-spacing: 1.6px; }}
    .tg   {{ font-size: 9px; fill: {C['tag']};  letter-spacing: 1.8px; }}

    .blink {{ animation: blink 1.15s steps(1) infinite; }}
    .pulse {{ animation: pulse 2.4s ease-in-out infinite; }}
    @keyframes blink {{ 0%,49% {{ opacity: 1 }} 50%,100% {{ opacity: 0 }} }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1 }} 50% {{ opacity: 0.25 }} }}
    @media (prefers-reduced-motion: reduce) {{
      .blink, .pulse {{ animation: none; }}
    }}
  </style>

  <rect width="{W}" height="{H}" rx="12" fill="{C['shell']}"/>
  <g clip-path="url(#win)">
    <rect width="{W}" height="{H}" fill="{C['win']}"/>
    <rect width="{W}" height="{TITLE_H}" fill="{C['bar']}"/>
    <rect y="{TITLE_H}" width="{W}" height="150" fill="url(#glow)"/>
  </g>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{C['edge']}"/>
  <line x1="0" y1="{TITLE_H}" x2="{W}" y2="{TITLE_H}" stroke="{C['edge']}"/>

  <!-- window chrome -->
  <circle cx="20" cy="16" r="4.5" fill="#e05c54" opacity="0.75"/>
  <circle cx="37" cy="16" r="4.5" fill="#d9a026" opacity="0.75"/>
  <circle cx="54" cy="16" r="4.5" fill="#33a852" opacity="0.75"/>
  <text class="bar" x="450" y="20" text-anchor="middle">abdallah@embedded  ~  %  ./profile<tspan class="blink" fill="#58a6ff"> &#9608;</tspan></text>
  <circle class="pulse" cx="797" cy="16" r="3.4" fill="{C['live']}"/>
  <text class="live" x="808" y="19.5">BUILDING</text>

  <!-- portrait -->
  <rect x="14" y="46" width="306" height="420" rx="8" fill="{C['panel']}" stroke="{C['panel_edge']}"/>
  <text class="lbl" x="26" y="64">PORTRAIT / ABDALLAH</text>
  <g class="art">
      {ART}
  </g>

  <!-- profile -->
  <rect x="332" y="46" width="554" height="420" rx="8" fill="{C['panel']}" stroke="{C['panel_edge']}"/>
  <text class="lbl" x="344" y="64">PROFILE / ENGINEER</text>
      {BODY}

  <line x1="0" y1="{FOOT_Y}" x2="{W}" y2="{FOOT_Y}" stroke="{C['edge']}"/>
  <text class="foot" x="450" y="504" text-anchor="middle">{FOOTER}</text>
</svg>
'''
    with open(OUT, "w") as fh:
        fh.write(svg)
    print(f"wrote {OUT}  ({len(svg) / 1024:.1f} KB, {COLS}x{ROWS} ASCII grid)")


if __name__ == "__main__":
    main()
