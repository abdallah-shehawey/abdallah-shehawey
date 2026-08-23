#!/usr/bin/env python3
"""Regenerate assets/banner.svg — the terminal-style header of the profile README.

Renders assets/portrait.jpg (the same photo GitHub uses as my avatar) as ASCII
art and composes it with a profile panel into one self-contained SVG.

    pip install pillow numpy
    python3 assets/make-banner.py

Two things here are deliberate and easy to break:

* GitHub serves this inside an <img>, so the cost that matters is raster, not
  page layout: every animation frame redraws the whole image. See art_svg and
  the per-layout `scanlines` / `art_bands` switches -- the phone card pays for
  its own smoothness, the desktop one keeps the full texture.
* The photo is a full scene — a person on stone steps in front of a wooden
  door. Mapping luminance straight onto a ramp turns that into noise, because
  the background carries as much contrast as the subject. So the subject is
  isolated by a hand-traced outline and the background is kept at a fraction of
  its density: present as a backdrop, never competing.
"""

import hashlib
import os
import re
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO = os.path.join(HERE, "portrait.jpg")
OUT = os.path.join(HERE, "banner.svg")
README = os.path.join(HERE, os.pardir, "README.md")

# --------------------------------------------------------------------- art
# Ramp ordered by measured ink coverage of each glyph, not by guesswork —
# a mis-ordered ramp is what makes ASCII portraits look like noise.
RAMP = " `.'~!;/=|ltsnXaw8mMQB@$"
CROP = (150, 0, 1120, 1254)        # trims the blurred padding off the square

# Subject outlines, traced by hand in photo pixels.
BODY = [
    (425, 80), (465, 60), (520, 58), (560, 78), (575, 115), (578, 175),
    (570, 225), (556, 265), (538, 295), (528, 330),
    (580, 340), (628, 368), (658, 405), (676, 455), (688, 500),
    (726, 515), (734, 690),
    (762, 692), (790, 745), (792, 792), (776, 832), (744, 864),
    (704, 886), (648, 896),
    # the near sneaker: right edge, toe, then along the sole
    (614, 940), (550, 990), (585, 1040), (610, 1072),
    (592, 1104), (468, 1106), (440, 1092),
    # ...straight onto the standing leg's right edge and down to its shoe
    (432, 1125), (433, 1180), (455, 1205), (478, 1232), (480, 1254),
    (330, 1254), (334, 1212), (338, 1178),
    # and back up that leg's left edge to the hip
    (328, 1135), (316, 1092), (305, 1050), (294, 1008), (285, 972),
    (268, 940), (250, 880), (242, 800), (238, 700),
    (240, 600), (246, 500), (252, 430), (266, 392), (296, 364),
    (338, 348), (386, 336), (432, 328), (452, 324),
    (448, 300), (428, 270), (412, 225), (408, 170), (412, 120),
]
CAR = [
    (848, 800), (852, 758), (872, 734), (902, 724), (935, 726), (958, 714),
    (968, 742), (1010, 745), (1050, 766), (1068, 800), (1064, 862),
    (1038, 900), (988, 918), (918, 918), (868, 900), (846, 858),
]

FEATHER, BLUR, GAMMA = 6, 0.9, 0.90
L_SIGMA, L_STRENGTH, L_MIX = 0.14, 2.0, 0.30
BACKDROP = 0.08                    # background density, as a fraction of full
SILHOUETTE = 0.14                  # minimum ink inside the subject outline
P_LO, P_HI, CUT = 1, 99, 0.05

def ascii_art(cols, rows):
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
                          .resize((cols, rows), Image.LANCZOS), np.float32) / 255.0

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

INFO = [
    ("head", "shehawey@embedded", None),
    ("kv", "Name:", "Abdallah Shehawey"),
    ("kv", "Role:", "Embedded Software Engineer"),
    ("kv", "Based:", "El Mahalla El Kubra, Gharbia, Egypt"),
    ("kv", "Mode:", "Bare-Metal / RTOS / Embedded Linux"),
    ("kv", "Writes:", "shinux.vercel.app / Notes from below the OS"),
    ("gap", None, None),
    ("sec", "BUILD.FOCUS", None),
    ("kv", "MCU:", "ARM Cortex-M, AVR, PIC, Arduino, ESP32"),
    ("kv", "RTOS:", "FreeRTOS, scheduling, IPC"),
    ("kv", "Vehicle:", "AUTOSAR, CAN, LIN, V2X safety"),
    ("kv", "Linux:", "Yocto, QEMU, drivers, Raspberry Pi"),
    ("gap", None, None),
    ("sec", "TOOLCHAIN", None),
    ("kv", "Code:", "C, C++, Python, Assembly, Bash"),
    ("kv", "IDE:", "CubeIDE, MPLAB X, Keil, Eclipse, VS Code"),
    ("kv", "Debug:", "JTAG, logic analyzer, scope"),
    ("kv", "Build:", "arm-none-eabi-gcc, avr-gcc, XC8, Make"),
    ("gap", None, None),
    ("tag", "FROM BARE-METAL DRIVERS TO EMBEDDED LINUX", None),
]

FOOTER = "EMBEDDED SYSTEMS  /  AUTOMOTIVE  /  RTOS &amp; AUTOSAR  /  EMBEDDED LINUX"
FOOTER_SM = "EMBEDDED  /  AUTOMOTIVE  /  RTOS  /  LINUX"
PROMPT = "shehawey@embedded  ~  %  ./profile"

MONO_ADVANCE = 0.6          # every monospace face in the stack below
MONO = ("ui-monospace,'SF Mono','JetBrains Mono','Fira Code',"
        "'DejaVu Sans Mono',Menlo,Consolas,monospace")

# ------------------------------------------------------------------ layouts
# Two shapes of the same card. The desktop one puts the panels side by side;
# the mobile one stacks them, because at phone width two columns of 12px
# monospace are unreadable.
DESKTOP = dict(
    out="banner.svg", W=900, H=556, bar_h=34, foot_y=516, foot_text=540,
    cols=84, rows=82, scanlines=True, art_bands=1, glyph_x=True,
    art=(28.0, 76.0, 316.0, 409.0),
    pa=(14, 46, 344, 454), pb=(370, 46, 516, 454),
    kx=394, lx0=478, lx1=530, vx=538, line=20.0, start=104.0, rule_x2=874,
    fs=dict(bar=10.5, lbl=8.5, hd=12, sc=10.5, kv=12, foot=9, live=9, tg=9),
    prompt_x=450, live_x=808, live_cx=797, foot=FOOTER, foot_ls=2.2,
)
MOBILE = dict(
    out="banner-mobile.svg", W=440, H=940, bar_h=30, foot_y=898, foot_text=920,
    cols=84, rows=82, scanlines=False, art_bands=8, glyph_x=False,
    art=(64.0, 70.0, 312.0, 404.0),
    pa=(10, 40, 420, 448), pb=(10, 500, 420, 386),
    kx=30, lx0=112, lx1=148, vx=156, line=17.0, start=544.0, rule_x2=412,
    fs=dict(bar=9, lbl=7.5, hd=10, sc=9, kv=9.5, foot=9, live=7.5, tg=8),
    prompt_x=196, live_x=336, live_cx=326, foot=FOOTER_SM, foot_ls=1.5,
)


INK = ((0xf0, 0xf6, 0xfc), (0x79, 0xc0, 0xff))   # art gradient, top-left -> bottom-right


def art_svg(art, L):
    """The ASCII grid. Two ways of writing it, and the layout picks.

    `glyph_x` gives every glyph its own absolute x and drops the spaces. It is
    the only form that is completely immune to whatever font the reader's
    browser forces on the document -- the grid cannot drift, because nothing
    about it comes from the font. It is also by far the most expensive thing
    to rasterise, and GitHub serves this inside an <img>, where the scanner
    sweep redraws the whole image every frame: 5033ms of raster per 3s against
    893ms, measured on a phone profile at 4x CPU throttle and dpr3.

    So the desktop card keeps it -- a laptop can afford it, and the owner
    browses with a forced font -- and the phone card takes one run per row
    instead, with the cell width coming from letter-spacing. That lands on the
    same grid for any face with the usual 0.6em advance and drifts only a few
    percent for one that does not.

    textLength would pin the width exactly and was tried both ways, but each
    mode is worse than either of these: lengthAdjust="spacing" places every
    glyph by hand for 2438ms, and "spacingAndGlyphs" scales the run, which
    welds runs of = and / into solid rules and smears the portrait.
    """
    ax, ay, aw, ah = L["art"]
    cols, rows = L["cols"], L["rows"]
    cw, ch = aw / cols, ah / rows
    fs = round(ch * 0.96, 2)

    if L.get("glyph_x"):
        out = []
        for r, line in enumerate(art):
            xs = [f"{round(ax + c * cw, 2):g}"
                  for c, ch_ in enumerate(line) if ch_ != " "]
            glyphs = line.replace(" ", "")
            if not glyphs:
                continue
            out.append(f'<text x="{" ".join(xs)}" '
                       f'y="{round(ay + (r + 0.82) * ch, 2):g}">{escape(glyphs)}</text>')
        return '<g class="art">\n      ' + "\n      ".join(out) + "\n    </g>", fs, None

    runs = []
    for r, line in enumerate(art):
        run = line.rstrip()
        if not run.strip():
            continue
        i0 = len(run) - len(run.lstrip())
        run = run[i0:]
        runs.append(
            f'<tspan x="{ax + i0 * cw:.2f}" y="{ay + (r + 0.82) * ch:.2f}" '
            f'textLength="{len(run) * cw:.2f}" lengthAdjust="spacingAndGlyphs" '
            f'xml:space="preserve">{escape(run)}</tspan>')

    bands = L.get("art_bands", 1)
    if bands <= 1:
        body = ['<text class="art">\n      ' + "\n      ".join(runs) + "\n    </text>"]
    else:
        # A gradient across five thousand glyphs costs 885ms of raster per 3s
        # where flat fills cost 776ms. Bands read identically at this size.
        body = []
        for i in range(bands):
            chunk = runs[i * len(runs) // bands:(i + 1) * len(runs) // bands]
            if not chunk:
                continue
            t = (i + 0.5) / bands
            col = "#%02x%02x%02x" % tuple(round(a + (b - a) * t)
                                          for a, b in zip(*INK))
            body.append(f'<text class="art" fill="{col}">\n      '
                        + "\n      ".join(chunk) + "\n    </text>")
    return "\n    ".join(body), fs, None


def info_svg(L):
    kx, x2, line = L["kx"], L["rule_x2"], L["line"]
    key_w = L["fs"]["kv"] * 0.62
    out, y = [], L["start"]
    for kind, a, b in INFO:
        if kind == "gap":
            y += line * 0.8
            continue
        if kind == "head":
            out.append(f'<text class="hd" x="{kx-10}" y="{y:g}">{escape(a)}</text>')
            out.append(f'<line class="rl" x1="{kx - 10 + len(a) * key_w + 14:g}" '
                       f'y1="{y-4:g}" x2="{x2}" y2="{y-4:g}"/>')
        elif kind == "tag":
            out.append(f'<text class="tg" x="{kx-10}" y="{y+6:g}">{escape(a)}</text>')
        elif kind == "sec":
            out.append(f'<text class="sc" x="{kx-10}" y="{y:g}">- {escape(a)}</text>')
            out.append(f'<line class="rl" x1="{kx - 10 + (len(a) + 3) * key_w + 14:g}" '
                       f'y1="{y-4:g}" x2="{x2}" y2="{y-4:g}"/>')
        else:
            out.append(f'<text class="k" x="{kx}" y="{y:g}">{escape(a)}</text>')
            out.append(f'<line class="ld" x1="{L["lx0"]}" y1="{y-3:g}" '
                       f'x2="{L["lx1"]}" y2="{y-3:g}"/>')
            out.append(f'<text class="v" x="{L["vx"]}" y="{y:g}">{escape(b)}</text>')
        y += line
    return "\n      ".join(out), y


def render(L, art):
    W, H, BAR = L["W"], L["H"], L["bar_h"]
    ART, FS, LS = art_svg(art, L)
    PANEL, _ = info_svg(L)
    f = L["fs"]
    pax, pay, paw, pah = L["pa"]
    pbx, pby, pbw, pbh = L["pb"]
    hx, hy = pax + paw / 2, pay + pah / 2          # portrait panel centre

    # A pattern tiled over the whole card is the single most expensive thing
    # to re-raster, and at phone scale its 4px pitch is invisible anyway:
    # dropping it took the phone card from 1292ms of raster per 3s to 851ms.
    scanlines = L.get("scanlines", True)
    SCANLINE_DEF = ('<pattern id="scanlines" width="4" height="4" patternUnits="userSpaceOnUse">\n'
                    '      <rect width="4" height="1" fill="#58a6ff" opacity="0.052"/>\n'
                    '    </pattern>\n') if scanlines else ""
    SCANLINES = (f'<rect width="{W}" height="{H}" rx="18" fill="url(#scanlines)"/>\n'
                 ) if scanlines else ""
    ART_FILL = "fill: url(#ink); " if L.get("art_bands", 1) <= 1 else ""
    ART_LS = "" if LS is None else f"letter-spacing: {LS}px; "

    live = ""
    if L["live_cx"] is not None:
        live = (f'<circle class="pulse" cx="{L["live_cx"]}" cy="{BAR/2:g}" r="3.4" fill="#58a6ff"/>\n'
                f'  <text class="live" x="{L["live_x"]}" y="{BAR/2 + 3.5:g}">BUILDING</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img"
     aria-label="Abdallah Shehawey - Embedded Software Engineer">
  <title>Abdallah Shehawey - Embedded Software Engineer</title>

  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#161b22"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#8b949e"/>
      <stop offset="0.48" stop-color="#58a6ff"/>
      <stop offset="1" stop-color="#8b949e"/>
    </linearGradient>
    <linearGradient id="ink" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f0f6fc"/><stop offset="1" stop-color="#79c0ff"/>
    </linearGradient>
    <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#58a6ff" stop-opacity="0"/>
      <stop offset="0.5" stop-color="#58a6ff" stop-opacity="0.46"/>
      <stop offset="1" stop-color="#8b949e" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="halo">
      <stop offset="0" stop-color="#58a6ff" stop-opacity="0.12"/>
      <stop offset="0.48" stop-color="#c9d1d9" stop-opacity="0.055"/>
      <stop offset="1" stop-color="#8b949e" stop-opacity="0"/>
    </radialGradient>
    {SCANLINE_DEF}    <pattern id="grid" width="44" height="44" patternUnits="userSpaceOnUse">
      <path d="M 44 0 H 0 V 44" fill="none" stroke="#c9d1d9" stroke-width="0.65" opacity="0.085"/>
      <circle cx="0" cy="0" r="1.2" fill="#58a6ff" opacity="0.13"/>
    </pattern>
    <clipPath id="card"><rect x="3" y="3" width="{W-6}" height="{H-6}" rx="16"/></clipPath>
    <clipPath id="portrait"><rect x="{pax}" y="{pay}" width="{paw}" height="{pah}" rx="12"/></clipPath>
  </defs>

  <style>
    text {{ font-family: {MONO}; white-space: pre; }}
    .bar  {{ font-size: {f['bar']}px;  fill: #8b949e; }}
    .lbl  {{ font-size: {f['lbl']}px;  fill: #6e7b8b; letter-spacing: 1.5px; }}
    .art  {{ font-size: {FS}px; {ART_LS}{ART_FILL}}}
    .hd   {{ font-size: {f['hd']}px;   fill: #f0f6fc; font-weight: 600; }}
    .sc   {{ font-size: {f['sc']}px;   fill: #8b949e; letter-spacing: 0.6px; }}
    .k    {{ font-size: {f['kv']}px;   fill: #58a6ff; font-weight: 600; }}
    .v    {{ font-size: {f['kv']}px;   fill: #c9d1d9; }}
    .rl   {{ stroke: #30363d; stroke-width: 1; }}
    .ld   {{ stroke: #3d4855; stroke-width: 1; stroke-dasharray: 1.5 3.5;
             stroke-linecap: round; }}
    .foot {{ font-size: {f['foot']}px; fill: #6e7b8b; letter-spacing: {L['foot_ls']}px; }}
    .live {{ font-size: {f['live']}px; fill: #58a6ff; letter-spacing: 1.6px; }}
    .tg   {{ font-size: {f['tg']}px;   fill: #8b949e; letter-spacing: 1.8px; }}
    .orbit {{ transform-box: view-box; }}

    @keyframes scan  {{ from {{ transform: translateY(0); }}
                       to   {{ transform: translateY({H + 90}px); }} }}
    @keyframes spin  {{ to {{ transform: rotate(360deg); }} }}
    @keyframes rspin {{ to {{ transform: rotate(-360deg); }} }}
    @keyframes blink {{ 0%,49% {{ opacity: 1 }} 50%,100% {{ opacity: 0 }} }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1 }} 50% {{ opacity: 0.25 }} }}

    @media (prefers-reduced-motion: no-preference) {{
      .motion-scan {{ animation: scan 8s linear infinite; }}
      .orbit--fwd  {{ animation: spin 42s linear infinite; }}
      .orbit--rev  {{ animation: rspin 34s linear infinite; }}
      .blink       {{ animation: blink 1.15s steps(1) infinite; }}
      .pulse       {{ animation: pulse 2.4s ease-in-out infinite; }}
    }}
    @media (prefers-reduced-motion: reduce) {{ .motion-scan {{ display: none; }} }}
  </style>

  <rect width="{W}" height="{H}" rx="18" fill="url(#bg)"/>
  {SCANLINES}  <rect x="3" y="3" width="{W-6}" height="{BAR}" rx="16" fill="#161b22" fill-opacity="0.84"/>

  <g clip-path="url(#card)">
    <g clip-path="url(#portrait)">
      <rect x="{pax}" y="{pay}" width="{paw}" height="{pah}" fill="url(#grid)"/>
    </g>
    <ellipse cx="{hx:g}" cy="{hy:g}" rx="{paw*0.49:g}" ry="{pah*0.48:g}" fill="url(#halo)"/>
    <ellipse class="orbit orbit--fwd" style="transform-origin:{hx:g}px {hy:g}px"
             cx="{hx:g}" cy="{hy:g}" rx="{paw*0.44:g}" ry="{pah*0.44:g}" fill="none"
             stroke="#c9d1d9" stroke-width="1" stroke-dasharray="3 14" opacity="0.13"/>
    <ellipse class="orbit orbit--rev" style="transform-origin:{hx:g}px {hy:g}px"
             cx="{hx:g}" cy="{hy:g}" rx="{paw*0.34:g}" ry="{pah*0.34:g}" fill="none"
             stroke="#8b949e" stroke-width="1" stroke-dasharray="28 24" opacity="0.10"/>

    <rect x="{pax}" y="{pay}" width="{paw}" height="{pah}" rx="12" fill="#161b22"
          fill-opacity="0.38" stroke="url(#edge)" stroke-opacity="0.42"/>
    <text class="lbl" x="{pax+12}" y="{pay+18}">PORTRAIT / ABDALLAH</text>
    {ART}

    <rect x="{pbx}" y="{pby}" width="{pbw}" height="{pbh}" rx="12" fill="#161b22"
          fill-opacity="0.42" stroke="url(#edge)" stroke-opacity="0.42"/>
    <text class="lbl" x="{pbx+12}" y="{pby+18}">PROFILE / ENGINEER</text>
      {PANEL}

    <rect class="motion-scan" x="0" y="-90" width="{W}" height="90"
          fill="url(#scan)" opacity="0.42" style="mix-blend-mode:screen"/>
  </g>

  <circle cx="24" cy="{BAR/2:g}" r="4.5" fill="#58a6ff" opacity="0.88"/>
  <circle cx="42" cy="{BAR/2:g}" r="4.5" fill="#8b949e" opacity="0.70"/>
  <circle cx="60" cy="{BAR/2:g}" r="4.5" fill="#8b949e" opacity="0.78"/>
  <text class="bar" x="{L['prompt_x']}" y="{BAR/2 + 3.5:g}" text-anchor="middle">{PROMPT}<tspan class="blink" fill="#58a6ff"> &#9608;</tspan></text>
  {live}

  <line x1="3" y1="{L['foot_y']}" x2="{W-3}" y2="{L['foot_y']}" stroke="#30363d"/>
  <text class="foot" x="{W/2:g}" y="{L['foot_text']}" text-anchor="middle">{L["foot"]}</text>

  <rect x="3" y="3" width="{W-6}" height="{H-6}" rx="16" fill="none"
        stroke="url(#edge)" stroke-width="2" opacity="0.76"/>
</svg>
'''


# ------------------------------------------------------------------ footer
# The sign-off strip under the README. Same two-variant treatment as the card:
# at 900px wide, 11px type shrinks to under 5 CSS px on a phone and is simply
# not readable, so the phone gets its own narrower box with larger type.
SIGNOFF = 'echo "Thanks for visiting!"'
TAGLINE = ("BUILT WITH PASSION", "POWERED BY CAFFEINE", "DEBUGGED WITH PATIENCE")
SHELL = "shehawey@embedded  ~  %  "

FOOT_WIDE = dict(out="footer.svg", W=900, H=140, x0=30, fs=13, dim=10.5,
                 dim_ls=2.0, rows=(40, 66, 94), sep=112, tags=((126, TAGLINE),))
FOOT_NARROW = dict(out="footer-mobile.svg", W=440, H=172, x0=20, fs=12, dim=9.5,
                   dim_ls=1.4, rows=(38, 64, 92), sep=112,
                   tags=((134, TAGLINE[:2]), (154, TAGLINE[2:])))


def footer_svg(L):
    W, H, x0, fs = L["W"], L["H"], L["x0"], L["fs"]
    adv = fs * MONO_ADVANCE
    cx = x0 + len(SHELL) * adv                 # where the command starts
    ax = cx + 5 * adv                          # ...and where its argument does
    r1, r2, r3 = L["rows"]
    tags = "\n  ".join(
        f'<text class="dim" x="{W/2:g}" y="{y}" text-anchor="middle">'
        f'{"  &#183;  ".join(parts)}</text>' for y, parts in L["tags"])

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img" aria-label="Profile Footer">
  <title>Profile Footer</title>

  <defs>
    <linearGradient id="glow" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1e60c8" stop-opacity="0.08"/>
      <stop offset="1" stop-color="#1e60c8" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="clip"><rect width="{W}" height="{H}" rx="12"/></clipPath>
  </defs>

  <style>
    text {{ font-family: {MONO}; white-space: pre; }}
    .prompt {{ font-size: {fs}px; fill: #5b6b80; }}
    .cmd    {{ font-size: {fs}px; fill: #58a6ff; }}
    .arg    {{ font-size: {fs}px; fill: #c5d2e0; }}
    .ok     {{ font-size: {fs}px; fill: #3fb950; }}
    .dim    {{ font-size: {L["dim"]}px; fill: #31435a; letter-spacing: {L["dim_ls"]}px; }}
    .dot    {{ stroke: #2b3a4d; stroke-width: 1; stroke-dasharray: 1.5 3.5;
               stroke-linecap: round; }}

    .blink  {{ animation: blink 1.15s steps(1) infinite; }}
    @keyframes blink {{ 0%,49% {{ opacity: 1 }} 50%,100% {{ opacity: 0 }} }}
    @media (prefers-reduced-motion: reduce) {{ .blink {{ animation: none; }} }}
  </style>

  <rect width="{W}" height="{H}" rx="12" fill="#070b10"/>
  <g clip-path="url(#clip)">
    <rect width="{W}" height="{H}" fill="#0b1017"/>
    <rect width="{W}" height="{H}" fill="url(#glow)"/>
  </g>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="#182231"/>

  <text class="prompt" x="{x0}" y="{r1}">{SHELL}</text>
  <text class="cmd" x="{cx:g}" y="{r1}">echo</text>
  <text class="arg" x="{ax:g}" y="{r1}">&#34;Thanks for visiting!&#34;</text>
  <text class="ok" x="{x0}" y="{r2}">Thanks for visiting!</text>

  <text class="prompt" x="{x0}" y="{r3}">{SHELL}</text>
  <text class="cmd" x="{cx:g}" y="{r3}">exit</text>
  <text class="arg" x="{ax:g}" y="{r3}">0</text>
  <text class="blink cmd" x="{ax + 2 * adv:g}" y="{r3}">&#9608;</text>

  <line class="dot" x1="{x0}" y1="{L["sep"]}" x2="{W-x0}" y2="{L["sep"]}"/>
  {tags}
</svg>
'''


# ----------------------------------------------------------------- divider
# The rule between sections. Drawn in one fixed accent -- no colour cycling --
# and with nothing that depends on the page background, so the same file reads
# correctly on GitHub's dark and light themes: the node is an outline, and the
# rule breaks either side of it rather than being knocked out by a filled box.
# The viewBox is 600 wide but it is served at 900, so the hairline scales UP on
# a desktop and only to about 1px on a phone instead of vanishing.
DIVIDER = dict(out="divider.svg", W=600, H=20, accent="#58a6ff")


def divider_svg(L):
    W, H, a = L["W"], L["H"], L["accent"]
    mid, gap = W / 2, 22
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="presentation" aria-hidden="true">
  <defs>
    <linearGradient id="fade-l" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{a}" stop-opacity="0"/>
      <stop offset="1" stop-color="{a}" stop-opacity="0.85"/>
    </linearGradient>
    <linearGradient id="fade-r" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{a}" stop-opacity="0.85"/>
      <stop offset="1" stop-color="{a}" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <rect x="0" y="{H/2 - 0.8:g}" width="{mid - gap:g}" height="1.6" rx="0.8" fill="url(#fade-l)"/>
  <rect x="{mid + gap:g}" y="{H/2 - 0.8:g}" width="{mid - gap:g}" height="1.6" rx="0.8" fill="url(#fade-r)"/>

  <g transform="translate({mid:g} {H/2:g})" fill="none" stroke="{a}">
    <rect x="-4.9" y="-4.9" width="9.8" height="9.8" rx="1.8"
          transform="rotate(45)" stroke-width="1.4" stroke-opacity="0.9"/>
    <circle r="1.9" fill="{a}" stroke="none"/>
  </g>
  <circle cx="{mid - gap - 12:g}" cy="{H/2:g}" r="1.5" fill="{a}" fill-opacity="0.55"/>
  <circle cx="{mid + gap + 12:g}" cy="{H/2:g}" r="1.5" fill="{a}" fill-opacity="0.55"/>
</svg>
'''


# ------------------------------------------------------------------- icons
# The bullets and section headings used stock emoji, which render in whatever
# each platform's emoji font decides and never match anything else here. These
# are 24px line icons in the one accent instead -- same colour and weight as
# the divider, and readable on GitHub's dark and light themes alike.
ICON_ACCENT = "#58a6ff"
ICONS = {
    "user": '<circle cx="12" cy="8" r="3.6"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
    "graduation": '<path d="M2.5 9 12 4.4 21.5 9 12 13.6 2.5 9Z"/>'
                  '<path d="M6.6 11v5.2c0 1.5 2.4 2.9 5.4 2.9s5.4-1.4 5.4-2.9V11"/>',
    "book": '<path d="M12 6.8C10.4 5.4 8.3 4.7 5.6 4.7H2.8v13.1h2.8c2.7 0 4.8.7 6.4 2.1"/>'
            '<path d="M12 6.8c1.6-1.4 3.7-2.1 6.4-2.1h2.8v13.1h-2.8c-2.7 0-4.8.7-6.4 2.1"/>'
            '<path d="M12 6.8V20"/>',
    "terminal": '<rect x="2.6" y="4.4" width="18.8" height="15.2" rx="2.4"/>'
                '<path d="m7 9.6 3 2.9-3 2.9"/><path d="M12.8 15.4h4.4"/>',
    "package": '<path d="m12 3 8.5 4.6v8.8L12 21l-8.5-4.6V7.6L12 3Z"/>'
               '<path d="m3.7 7.7 8.3 4.5 8.3-4.5"/><path d="M12 12.2V21"/>',
    "pen": '<path d="M4 20.2h4.2L20 8.4a2.9 2.9 0 0 0-4.1-4.1L4 16v4.2Z"/>'
           '<path d="m14.4 5.9 3.7 3.7"/>',
    "star": '<path d="m12 3.1 2.78 5.63 6.22.9-4.5 4.39 1.06 6.19L12 17.29 '
            '6.44 20.21 7.5 14.02 3 9.63l6.22-.9L12 3.1Z"/>',
    "cpu": '<rect x="6.2" y="6.2" width="11.6" height="11.6" rx="1.6"/>'
           '<rect x="9.6" y="9.6" width="4.8" height="4.8" rx="0.8"/>'
           '<path d="M9.5 2.6v3.6M14.5 2.6v3.6M9.5 17.8v3.6M14.5 17.8v3.6'
           'M2.6 9.5h3.6M2.6 14.5h3.6M17.8 9.5h3.6M17.8 14.5h3.6"/>',
    "target": '<circle cx="12" cy="12" r="8.4"/><circle cx="12" cy="12" r="4.6"/>'
              '<circle cx="12" cy="12" r="1.4" fill="' + ICON_ACCENT + '" stroke="none"/>',
    "globe": '<circle cx="12" cy="12" r="8.6"/><path d="M3.4 12h17.2"/>'
             '<path d="M12 3.4c2.3 2.4 3.6 5.4 3.6 8.6S14.3 18.2 12 20.6'
             'C9.7 18.2 8.4 15.2 8.4 12S9.7 5.8 12 3.4Z"/>',
    "trending": '<path d="m3.5 16.8 5.6-5.6 3.6 3.6 7.8-7.8"/><path d="M15.4 7h5.1v5.1"/>',
    "chart": '<path d="M4 20.4h16"/><path d="M7.6 20.4v-6.2M12 20.4V6.4M16.4 20.4v-9.4"/>',
}


def icon_svg(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
            f'viewBox="0 0 24 24" fill="none" stroke="{ICON_ACCENT}" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
            f'role="presentation" aria-hidden="true">{body}</svg>\n')


def main():
    grids = {}
    stamps = {}
    for L in (DESKTOP, MOBILE):
        key = (L["cols"], L["rows"])
        if key not in grids:
            grids[key] = ascii_art(*key)
        svg = render(L, grids[key])
        path = os.path.join(HERE, L["out"])
        with open(path, "w") as fh:
            fh.write(svg)
        stamps[L["out"]] = hashlib.sha256(svg.encode()).hexdigest()[:10]
        print(f"wrote {L['out']}  ({len(svg)/1024:.1f} KB, {L['W']}x{L['H']})")

    icons_dir = os.path.join(HERE, "icons")
    os.makedirs(icons_dir, exist_ok=True)
    for name, body in ICONS.items():
        svg = icon_svg(body)
        with open(os.path.join(icons_dir, f"{name}.svg"), "w") as fh:
            fh.write(svg)
        stamps[f"icons/{name}.svg"] = hashlib.sha256(svg.encode()).hexdigest()[:10]
    print(f"wrote {len(ICONS)} icons in assets/icons/")

    svg = divider_svg(DIVIDER)
    with open(os.path.join(HERE, DIVIDER["out"]), "w") as fh:
        fh.write(svg)
    stamps[DIVIDER["out"]] = hashlib.sha256(svg.encode()).hexdigest()[:10]
    print(f"wrote {DIVIDER['out']}  ({len(svg)/1024:.1f} KB, "
          f"{DIVIDER['W']}x{DIVIDER['H']})")

    for L in (FOOT_WIDE, FOOT_NARROW):
        svg = footer_svg(L)
        with open(os.path.join(HERE, L["out"]), "w") as fh:
            fh.write(svg)
        stamps[L["out"]] = hashlib.sha256(svg.encode()).hexdigest()[:10]
        print(f"wrote {L['out']}  ({len(svg)/1024:.1f} KB, {L['W']}x{L['H']})")

    # GitHub caches README images by URL, so a rewritten SVG keeps serving the
    # old picture for hours. Stamp each reference with a hash of its file.
    with open(README) as fh:
        readme = fh.read()
    for name, digest in stamps.items():
        readme = re.sub(rf'(assets/{re.escape(name)})(\?v=[0-9a-f]+)?"',
                        rf'\1?v={digest}"', readme)
    with open(README, "w") as fh:
        fh.write(readme)
    print("stamped README:", ", ".join(f"{k}?v={v}" for k, v in stamps.items()))


if __name__ == "__main__":
    main()
