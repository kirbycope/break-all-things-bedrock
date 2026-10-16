"""Build the 1920x1080 thumbnail for YouTube and Planet Minecraft, and the 960x540 repository preview.

Everything it needs is committed: the birch glade from the trailer in assets/background.png, the diamond vein
breaking in assets/vein.png, the player skin in assets/skin.png, the Timber Axe texture and Passion One in tools/fonts/.

    python tools/make_thumbnail.py
    python tools/make_thumbnail.py --no-preview
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

import skin_render

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONT = os.path.join(HERE, "fonts", "PassionOne-Black.ttf")

W, H = 1920, 1080

STYLES = {
    "white":   dict(top=(255, 255, 255), bot=(180, 184, 188), side=(138, 142, 146)),
    # the Vein Pickaxe's diamond, against the glade's greens and blues
    "diamond": dict(top=(168, 255, 244), bot=(32, 197, 181), side=(10, 92, 84)),
}

TITLE = [
    dict(text="BREAK ALL", style="diamond", cap=150, arc=7),
    dict(text="THE THINGS!", style="diamond", cap=150, arc=7),
    dict(text="BEDROCK", style="white", cap=98, arc=-10),
]

AXE = os.path.join(ROOT, "development_resource_packs", "break_all_things", "textures", "items", "timber_axe.png")
VEIN_CROP = (300, 60, 1740, 870)      # the hole, the diamonds in the air and the lapis left standing
STEVE_BOX = (840, 450, 1100, 1030)    # the player the trailer filmed, painted out of the plate

STROKE, DEPTH, EXTRUDE_DEG, TRACK = 13, 8, 90, 5


# --------------------------------------------------------------------------- type

def _cap_ratio(path):
    f = ImageFont.truetype(path, 400)
    box = f.getbbox("H")
    return (box[3] - box[1]) / 400.0


def _layout(font, text, track):
    xs, x = [], 0.0
    for ch in text:
        xs.append(x)
        x += font.getlength(ch) + track
    return xs, max(0.0, x - track)


def _advances(cap, text):
    font = ImageFont.truetype(FONT, int(round(cap / _cap_ratio(FONT))))
    return sum(font.getlength(c) for c in text)


def _track_for(cap, text, width):
    """Letter spacing that makes this word exactly `width` wide. Justifying on
    tracking keeps the letterforms; stretching the bitmap would not."""
    n = len(text)
    if n < 2:
        return TRACK
    return (width - _advances(cap, text)) / (n - 1)


def render_line(text, cap, style, track=TRACK, hscale=1.0, arc=0.0):
    """One word with the outline, extrude, gradient face and drop shadow."""
    pal = STYLES[style]
    size = int(round(cap / _cap_ratio(FONT)))
    font = ImageFont.truetype(FONT, size)
    xs, natural = _layout(font, text, track)

    rad = math.radians(EXTRUDE_DEG)
    dx, dy = math.cos(rad), math.sin(rad)
    pad = STROKE + DEPTH + 60
    cw = int(natural + pad * 2)
    ch = int(cap + size * 0.6 + pad * 2)
    base_y = pad + cap

    def draw_pass(img, fill, stroke_fill, stroke_w, ox, oy):
        d = ImageDraw.Draw(img)
        for ch_, x in zip(text, xs):
            d.text((pad + x + ox, base_y + oy), ch_, font=font, fill=fill,
                   anchor="ls", stroke_width=stroke_w, stroke_fill=stroke_fill)

    # the black shell around the whole extruded solid
    shell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    for d_ in range(DEPTH, -1, -1):
        draw_pass(shell, (11, 11, 11, 255), (11, 11, 11, 255), STROKE,
                  dx * d_, dy * d_)

    # side faces
    sides = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    for d_ in range(DEPTH, 0, -1):
        draw_pass(sides, pal["side"] + (255,), None, 0, dx * d_, dy * d_)

    # top face, masked so the gradient runs down the cap height
    face_mask = Image.new("L", (cw, ch), 0)
    draw_pass(face_mask, 255, None, 0, 0, 0)
    grad = Image.new("RGB", (1, ch))
    gp = grad.load()
    for y in range(ch):
        t = (y - (base_y - cap)) / max(1.0, cap)
        t = min(1.0, max(0.0, t))
        k = t / 0.78 if t < 0.78 else (1.0 - t) / 0.22
        k = min(1.0, max(0.0, k))
        gp[0, y] = tuple(int(a + (b - a) * k) for a, b in zip(pal["top"], pal["bot"]))
    face = grad.resize((cw, ch), Image.NEAREST).convert("RGBA")
    face.putalpha(face_mask)

    line = Image.alpha_composite(shell, sides)
    line = Image.alpha_composite(line, face)

    # drop shadow, cast off the far face
    sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sh.putalpha(line.split()[3])
    sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 150))
    sh.putalpha(ImageChops.multiply(line.split()[3],
                                    Image.new("L", (cw, ch), 150)))
    sh = sh.filter(ImageFilter.GaussianBlur(11))
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out.alpha_composite(sh, (9, 13))
    out = Image.alpha_composite(out, line)

    if hscale != 1.0:
        out = out.resize((max(1, int(cw * hscale)), ch), Image.LANCZOS)
    if arc:
        out = _arc(out, arc)
    return out, natural


def _arc(img, bend):
    """Slide every column along a parabola, zero at both ends."""
    w, h = img.size
    pad = int(abs(bend)) + 2
    out = Image.new("RGBA", (w, h + pad * 2), (0, 0, 0, 0))
    for x in range(w):
        t = (x / (w - 1)) * 2 - 1 if w > 1 else 0.0
        off = bend * (1 - t * t)
        out.paste(img.crop((x, 0, x + 1, h)), (x, int(round(pad + off))))
    return out


def render_title():
    """Three lines set left, each at its natural width."""
    pieces, widths = [], []
    for ln in TITLE:
        piece, natural = render_line(ln["text"], ln["cap"], ln["style"],
                                     track=TRACK, arc=ln["arc"])
        pieces.append(piece)
        widths.append(natural)

    gap = 6
    total = sum(ln["cap"] for ln in TITLE) + gap * (len(TITLE) - 1)
    pad = 190
    block = Image.new("RGBA", (int(max(widths)) + pad * 2, int(total) + pad * 2),
                      (0, 0, 0, 0))
    y = pad
    for ln, piece in zip(TITLE, pieces):
        inner_pad = STROKE + DEPTH + 60
        arc_pad = int(abs(ln["arc"])) + 2
        block.alpha_composite(piece, (pad - inner_pad, int(y - inner_pad - arc_pad)))
        y += ln["cap"] + gap
    return block, pad, int(max(widths)), int(total)


# ------------------------------------------------------------------------ scene


def _grade(img, sat=1.5, contrast=1.14, bright=1.03):
    img = ImageEnhance.Color(img).enhance(sat)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    return ImageEnhance.Brightness(img).enhance(bright)


def _vignette(img, strength=0.3):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    nx = (xx / (w - 1)) * 2 - 1
    ny = (yy / (h - 1)) * 2 - 1
    r = np.sqrt(nx ** 2 + ny ** 2) / math.sqrt(2)
    k = 1.0 - strength * np.clip((r - 0.55) / 0.45, 0, 1) ** 1.6
    arr = np.asarray(img.convert("RGB")).astype(np.float32) * k[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _card(img, rim=9, shadow=30):
    """The white rim and drop shadow the author's thumbnails give anything
    lifted out of the scene."""
    pad = rim + shadow + 20
    out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 155), (pad, pad), Image.new("L", img.size, 255))
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(shadow * 0.55)))
    ring = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ring.paste((255, 255, 255, 255), (pad - rim, pad - rim),
               Image.new("L", (img.width + rim * 2, img.height + rim * 2), 255))
    out = Image.alpha_composite(out, ring)
    out.alpha_composite(img.convert("RGBA"), (pad, pad))
    return out


def build():
    plate = Image.open(os.path.join(ROOT, "assets", "background.png")).convert("RGB")

    # the glade behind, softened and pushed back so the title and the card carry
    backdrop = _patch_out(plate, STEVE_BOX).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.4))
    canvas = _grade(backdrop, sat=1.34, contrast=1.08, bright=0.97).convert("RGBA")

    # the vein the moment it breaks, lifted out on a card
    vein = Image.open(os.path.join(ROOT, "assets", "vein.png")).convert("RGB").crop(VEIN_CROP)
    vein = _grade(vein.resize((800, int(800 * vein.height / vein.width)), Image.LANCZOS), sat=1.3, contrast=1.12, bright=1.12)
    canvas.alpha_composite(_card(vein).rotate(3, expand=True, resample=Image.BICUBIC), (1030, 420))

    # the player, big in the corner, holding the Timber Axe out toward the vein
    swing = {
        "head":      (-6, 24, 0),
        "body":      (0, 10, 0),
        "arm_right": (-4, 0, -9),
        "arm_left":  (-80, 0, 34),
        "leg_right": (7, 0, -7),
        "leg_left":  (-8, 0, 8),
    }
    char = skin_render.render(os.path.join(ROOT, "assets", "skin.png"),
                              height=820, yaw=24, pitch=3, outline=11, pose=swing)
    char_pos = (560, H - char.height + 250)
    canvas.alpha_composite(char, char_pos)

    # the axe in the outstretched hand: the grip, near the sprite's bottom left, sits on the arm's far end
    a = np.asarray(char.split()[3])
    ys, xs = np.nonzero(a > 0)
    hand = (char_pos[0] + int(xs.max()), char_pos[1] + int(ys[xs == xs.max()].mean()))
    axe = Image.open(AXE).convert("RGBA").resize((360, 360), Image.NEAREST)
    axe = _card_outline(axe, 11)
    canvas.alpha_composite(axe, (hand[0] + AXE_AT[0], hand[1] - axe.height + AXE_AT[1]))

    block, pad, tw, th = render_title()
    block = block.rotate(-2.0, expand=True, resample=Image.BICUBIC)
    canvas.alpha_composite(block, (86 - pad, 74 - pad))

    out = _vignette(canvas.convert("RGB"), 0.28)
    return _grade(out, sat=1.06, contrast=1.04, bright=1.0)


AXE_AT = (-80, 70)   # the grip, a little up the handle from its end, at the hand


def _patch_out(plate, box):
    """Paint a box out of the plate with the strip beside it, mirrored; enough once the backdrop is blurred."""
    left, top, right, bottom = box
    width = right - left
    donor = plate.crop((max(0, left - width), top, left, bottom)).transpose(Image.FLIP_LEFT_RIGHT)
    out = plate.copy()
    out.paste(donor.resize((width, bottom - top), Image.LANCZOS), (left, top))
    return out


def _card_outline(img, width):
    """The white outline the player gets, around a sprite."""
    alpha = img.split()[3].filter(ImageFilter.MaxFilter(width * 2 + 1))
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.putalpha(alpha)
    return Image.alpha_composite(out, img)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "thumbnail.png"))
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    img = build()
    img.save(args.out)
    print(f"wrote {args.out} {img.size[0]}x{img.size[1]}")

    if not args.no_preview:
        # the repository preview is 960x540, written by the project's own tool
        dest = os.path.join(ROOT, "break-all-things-bedrock.png")
        subprocess.check_call([sys.executable,
                               os.path.join(HERE, "make_preview.py"),
                               args.out, dest])


if __name__ == "__main__":
    main()
