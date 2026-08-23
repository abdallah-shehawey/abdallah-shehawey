#!/usr/bin/env python3
"""Regenerate assets/banner.svg — the terminal-style header of the profile README.

Renders assets/portrait.jpg (the same photo GitHub uses as my avatar) as ASCII
art and composes it with a profile panel into one self-contained SVG.

    pip install pillow numpy
    python3 assets/make-banner.py

Two things here are deliberate and easy to break:

* Every glyph carries its own absolute x and spaces are dropped, so the
  character grid survives font substitution and any whitespace handling.
* The photo is a full scene — a person on stone steps in front of a wooden
  door. Mapping luminance straight onto a ramp turns that into noise, because
  the background carries as much contrast as the subject. So the subject is
  isolated by a hand-traced outline and the background is kept at a fraction of
  its density: present as a backdrop, never competing.
"""

import os
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO = os.path.join(HERE, "portrait.jpg")
OUT = os.path.join(HERE, "banner.svg")

# --------------------------------------------------------------------- art
# Ramp ordered by measured ink coverage of each glyph, not by guesswork —
# a mis-ordered ramp is what makes ASCII portraits look like noise.
RAMP = " `.'~!;/=|ltsnXaw8mMQB@$"
COLS, ROWS = 84, 82
CROP = (150, 0, 1120, 1254)        # trims the blurred padding off the square

# Subject outlines, traced by hand in photo pixels.
BODY = [
    (425, 80), (465, 60), (520, 58), (560, 78), (575, 115), (578, 175),
    (570, 225), (556, 265), (538, 295), (528, 330),
    (580, 340), (628, 368), (658, 405), (676, 455), (688, 500),
    (724, 520), (730, 700), (726, 812),
    (700, 832), (664, 862), (636, 900), (614, 940), (606, 990),
    (588, 1040), (556, 1072), (505, 1085), (452, 1075), (416, 1042),
    (398, 995), (394, 946),
    (350, 1000), (340, 1080), (360, 1180), (372, 1254),
    (490, 1254), (480, 1160), (455, 1080), (425, 1020), (400, 980),
    (300, 990), (268, 940), (250, 880), (242, 800), (238, 700),
    (240, 600), (246, 500), (252, 430), (266, 392), (296, 364),
    (338, 348), (386, 336), (432, 328), (452, 324),
    (448, 300), (428, 270), (412, 225), (408, 170), (412, 120),
]
CAR = [
    (842, 790), (848, 742), (872, 712), (910, 696), (938, 660), (946, 690),
    (1002, 700), (1046, 716), (1072, 764), (1068, 830), (1030, 872),
    (960, 886), (890, 878), (848, 848),
]

FEATHER, BLUR, GAMMA = 6, 0.9, 0.90
L_SIGMA, L_STRENGTH, L_MIX = 0.14, 2.0, 0.30
BACKDROP = 0.08                    # background density, as a fraction of full
SILHOUETTE = 0.14                  # minimum ink inside the subject outline
P_LO, P_HI, CUT = 1, 99, 0.05


def ascii_art():
    photo = Image.open(PHOTO).convert("L")

    mask = Image.new("L", photo.size, 0)
    pen = ImageDraw.Draw(mask)
    pen.polygon(BODY, fill=255)
    pen.polygon(CAR, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(FEATHER)).crop(CROP)

    im = photo.crop(CROP).filter(ImageFilter.GaussianBlur(BLUR))
    g = np.asarray(im, np.float32) / 255.0

    # A touch of local contrast lifts detail out of the black suit without
    # flattening the large shapes that make the pose readable.
    sigma = L_SIGMA * (CROP[2] - CROP[0])
    lp = np.asarray(Image.fromarray((g * 255).astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(sigma)), np.float32) / 255.0
    flat = np.clip(0.5 + L_STRENGTH * (g - lp), 0, 1)
    tone = np.clip(L_MIX * flat + (1 - L_MIX) * g, 0, 1)

    def cells(a):
        return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
                          .resize((COLS, ROWS), Image.LANCZOS), np.float32) / 255.0

    t, m = cells(tone), cells(np.asarray(mask, np.float32) / 255.0)
    lo, hi = np.percentile(t, P_LO), np.percentile(t, P_HI)
    t = np.clip((t - lo) / max(hi - lo, 1e-6), 0, 1)

    # Bright -> dense. On a dark panel that reproduces the photo the way a
    # screen shows it; the usual dark->dense mapping turns the black suit and
    # the dark plaque into one solid blob with no structure.
    dens = t ** GAMMA
    dens = np.maximum(dens, SILHOUETTE * m)   # or the black suit vanishes
    dens *= BACKDROP + (1 - BACKDROP) * m
    dens[dens < CUT] = 0.0

    idx = (dens * (len(RAMP) - 1)).round().astype(int)
    return ["".join(RAMP[i] for i in row) for row in idx]


# ------------------------------------------------------------------ layout
W, H = 900, 556
TITLE_H, FOOT_Y = 32, 516
AX, AY, AW, AH = 28.0, 76.0, 316.0, 409.0     # art box, matches CROP's aspect
KX, LX0, LX1, VX, LINE = 394, 478, 530, 538, 20.0

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
    ("kv", "Mode:", "Bare-Metal / RTOS / Embedded Linux"),
    ("kv", "Writes:", "shinux.vercel.app / Notes from below the OS"),
    ("gap", None, None),
    ("sec", "BUILD.FOCUS", None),
    ("kv", "MCU:", "ARM Cortex-M, AVR, PIC"),
    ("kv", "RTOS:", "FreeRTOS, scheduling, IPC"),
    ("kv", "Vehicle:", "AUTOSAR, CAN, LIN, V2X safety"),
    ("kv", "Linux:", "Yocto, QEMU, drivers, Raspberry Pi"),
    ("gap", None, None),
    ("sec", "TOOLCHAIN", None),
    ("kv", "Code:", "C, C++, Python, Assembly"),
    ("kv", "IDE:", "CubeIDE, MPLAB X, Keil, Eclipse, VS Code"),
    ("kv", "Debug:", "JTAG, logic analyzer, scope"),
    ("kv", "Build:", "arm-none-eabi-gcc, avr-gcc, XC8, Make"),
    ("gap", None, None),
    ("tag", "FROM BARE-METAL DRIVERS TO EMBEDDED LINUX", None),
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
    return "\n      ".join(out), round(ch * 0.96, 2)


def info_svg():
    out, y = [], 104.0
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
    ART, FS = art_svg(ascii_art())
    PANEL = info_svg()

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img"
     aria-label="Abdallah Shehawey - Embedded Software Engineer">
  <title>Abdallah Shehawey - Embedded Software Engineer</title>

  <defs>
    <linearGradient id="ink" x1="0" y1="0" x2="0.25" y2="1">
      <stop offset="0"    stop-color="#d6e6ff"/>
      <stop offset="0.35" stop-color="#8cc0ff"/>
      <stop offset="0.75" stop-color="#5b95e6"/>
      <stop offset="1"    stop-color="#3d74c2"/>
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
    .sc   {{ font-size: 10.5px; fill: {C['sec']}; letter-spacing: 0.6px; }}
    .k    {{ font-size: 12px;   fill: {C['key']}; }}
    .v    {{ font-size: 12px;   fill: {C['val']}; }}
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
    <rect y="{TITLE_H}" width="{W}" height="170" fill="url(#glow)"/>
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
  <rect x="14" y="46" width="344" height="454" rx="8" fill="{C['panel']}" stroke="{C['panel_edge']}"/>
  <text class="lbl" x="26" y="64">PORTRAIT / ABDALLAH</text>
  <g class="art">
      {ART}
  </g>

  <!-- profile -->
  <rect x="370" y="46" width="516" height="454" rx="8" fill="{C['panel']}" stroke="{C['panel_edge']}"/>
  <text class="lbl" x="382" y="64">PROFILE / ENGINEER</text>
      {PANEL}

  <line x1="0" y1="{FOOT_Y}" x2="{W}" y2="{FOOT_Y}" stroke="{C['edge']}"/>
  <text class="foot" x="450" y="540" text-anchor="middle">{FOOTER}</text>
</svg>
'''
    with open(OUT, "w") as fh:
        fh.write(svg)
    print(f"wrote {OUT}  ({len(svg) / 1024:.1f} KB, {COLS}x{ROWS} ASCII grid)")


if __name__ == "__main__":
    main()
