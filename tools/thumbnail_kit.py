"""The shared half of every project thumbnail: the extruded title, cards, outlines, grading and the vignette.

Copied into a project's tools/ beside its own make_thumbnail.py, which composes the scene. Nothing here knows about
a particular project; the font, the colours and the title lines are passed in.

    from thumbnail_kit import Title, card, outline, grade, vignette, patch_out, far_point

    title = Title(font="tools/fonts/Bangers-Regular.ttf", styles={"burst": dict(top=..., bot=..., side=...)},
                  lines=[dict(text="BREAK ALL", style="burst", cap=168, arc=7), ...])
    canvas.alpha_composite(*title.place(x=86, y=74, tilt=-2.0))
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1920, 1080
STROKE, DEPTH, EXTRUDE_DEG, TRACK = 13, 8, 90, 5

WHITE = dict(top=(255, 255, 255), bot=(196, 200, 206), side=(120, 124, 132))


# --------------------------------------------------------------------------- type

class Title:
    """Lines of extruded type set ragged left, each at its natural width.

    A style is three colours: the top of the face, the bottom of the face, and the extruded side. A line is
    dict(text, style, cap, arc): cap is the capital height in pixels, arc bends the line along a parabola (positive
    sags in the middle, negative humps)."""

    def __init__(self, font: str, styles: dict, lines: list[dict], gap: int = 6, track: float = TRACK):
        self.font, self.styles, self.lines, self.gap, self.track = font, styles, lines, gap, track
        box = ImageFont.truetype(font, 400).getbbox("H")
        self.cap_ratio = (box[3] - box[1]) / 400.0

    def line(self, text: str, cap: float, style: str, arc: float = 0.0) -> tuple[Image.Image, float]:
        """One line with the black shell, the extruded sides, the gradient face and a drop shadow."""
        pal = self.styles[style]
        size = int(round(cap / self.cap_ratio))
        font = ImageFont.truetype(self.font, size)
        xs, x = [], 0.0
        for ch_ in text:
            xs.append(x)
            x += font.getlength(ch_) + self.track
        natural = max(0.0, x - self.track)

        rad = math.radians(EXTRUDE_DEG)
        dx, dy = math.cos(rad), math.sin(rad)
        pad = STROKE + DEPTH + 60
        cw, ch = int(natural + pad * 2), int(cap + size * 0.6 + pad * 2)
        base_y = pad + cap

        def draw_pass(img, fill, stroke_fill, stroke_w, ox, oy):
            d = ImageDraw.Draw(img)
            for c, cx in zip(text, xs):
                d.text((pad + cx + ox, base_y + oy), c, font=font, fill=fill, anchor="ls",
                       stroke_width=stroke_w, stroke_fill=stroke_fill)

        shell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        for d_ in range(DEPTH, -1, -1):
            draw_pass(shell, (11, 11, 11, 255), (11, 11, 11, 255), STROKE, dx * d_, dy * d_)
        sides = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        for d_ in range(DEPTH, 0, -1):
            draw_pass(sides, pal["side"] + (255,), None, 0, dx * d_, dy * d_)

        # the face, its gradient running down the cap height and lifting again at the foot
        face_mask = Image.new("L", (cw, ch), 0)
        draw_pass(face_mask, 255, None, 0, 0, 0)
        grad = Image.new("RGB", (1, ch))
        gp = grad.load()
        for y in range(ch):
            t = min(1.0, max(0.0, (y - (base_y - cap)) / max(1.0, cap)))
            k = min(1.0, max(0.0, t / 0.78 if t < 0.78 else (1.0 - t) / 0.22))
            gp[0, y] = tuple(int(a + (b - a) * k) for a, b in zip(pal["top"], pal["bot"]))
        face = grad.resize((cw, ch), Image.NEAREST).convert("RGBA")
        face.putalpha(face_mask)
        solid = Image.alpha_composite(Image.alpha_composite(shell, sides), face)

        sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 150))
        sh.putalpha(ImageChops.multiply(solid.split()[3], Image.new("L", (cw, ch), 150)))
        sh = sh.filter(ImageFilter.GaussianBlur(11))
        out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        out.alpha_composite(sh, (9, 13))
        out = Image.alpha_composite(out, solid)
        return (_arc(out, arc) if arc else out), natural

    def block(self) -> tuple[Image.Image, int]:
        """Every line stacked into one transparent block, and the padding around the type inside it."""
        pieces = [self.line(ln["text"], ln["cap"], ln["style"], ln.get("arc", 0.0)) for ln in self.lines]
        total = sum(ln["cap"] for ln in self.lines) + self.gap * (len(self.lines) - 1)
        pad = 190
        out = Image.new("RGBA", (int(max(w for _, w in pieces)) + pad * 2, int(total) + pad * 2), (0, 0, 0, 0))
        y = pad
        inner = STROKE + DEPTH + 60
        for ln, (piece, _) in zip(self.lines, pieces):
            out.alpha_composite(piece, (pad - inner, int(y - inner - int(abs(ln.get("arc", 0.0))) - 2)))
            y += ln["cap"] + self.gap
        return out, pad

    def place(self, x: int, y: int, tilt: float = -2.0) -> tuple[Image.Image, tuple[int, int]]:
        """The block tilted, and where to composite it so the type's top left lands at x, y."""
        block, pad = self.block()
        return block.rotate(tilt, expand=True, resample=Image.BICUBIC), (x - pad, y - pad)


def _arc(img: Image.Image, bend: float) -> Image.Image:
    """Slide every column along a parabola, zero at both ends."""
    w, h = img.size
    pad = int(abs(bend)) + 2
    out = Image.new("RGBA", (w, h + pad * 2), (0, 0, 0, 0))
    for x in range(w):
        t = (x / (w - 1)) * 2 - 1 if w > 1 else 0.0
        out.paste(img.crop((x, 0, x + 1, h)), (x, int(round(pad + bend * (1 - t * t)))))
    return out


# ------------------------------------------------------------------------ scene

def grade(img: Image.Image, sat: float = 1.5, contrast: float = 1.14, bright: float = 1.03) -> Image.Image:
    img = ImageEnhance.Color(img).enhance(sat)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    return ImageEnhance.Brightness(img).enhance(bright)


def vignette(img: Image.Image, strength: float = 0.3) -> Image.Image:
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx / (w - 1)) * 2 - 1) ** 2 + ((yy / (h - 1)) * 2 - 1) ** 2) / math.sqrt(2)
    k = 1.0 - strength * np.clip((r - 0.55) / 0.45, 0, 1) ** 1.6
    arr = np.asarray(img.convert("RGB")).astype(np.float32) * k[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def card(img: Image.Image, rim: int = 9, shadow: int = 30) -> Image.Image:
    """The white rim and drop shadow given anything lifted out of the scene, a frame of the feature working."""
    pad = rim + shadow + 20
    out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 155), (pad, pad), Image.new("L", img.size, 255))
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(shadow * 0.55)))
    ring = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ring.paste((255, 255, 255, 255), (pad - rim, pad - rim), Image.new("L", (img.width + rim * 2, img.height + rim * 2), 255))
    out = Image.alpha_composite(out, ring)
    out.alpha_composite(img.convert("RGBA"), (pad, pad))
    return out


def outline(img: Image.Image, width: int = 11) -> Image.Image:
    """The white outline the rendered player gets, around any sprite (an item texture blown up with NEAREST)."""
    alpha = img.split()[3].filter(ImageFilter.MaxFilter(width * 2 + 1))
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.putalpha(alpha)
    return Image.alpha_composite(out, img)


def patch_out(plate: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """Paint a box out of a plate with the strip to its left, mirrored. Enough once the backdrop is blurred: use it
    for the player the trailer filmed, a HUD element, anything the thumbnail redraws bigger in the same place."""
    left, top, right, bottom = box
    width = right - left
    donor = plate.crop((max(0, left - width), top, left, bottom)).transpose(Image.FLIP_LEFT_RIGHT)
    out = plate.copy()
    out.paste(donor.resize((width, bottom - top), Image.LANCZOS), (left, top))
    return out


def far_point(char: Image.Image, side: str = "right") -> tuple[int, int]:
    """Where a rendered player's outstretched hand is, inside the image: the farthest inked pixel on that side
    ("right", "left" or "top"). Add the player's position on the canvas to place a held item there."""
    a = np.asarray(char.split()[3]) > 0
    ys, xs = np.nonzero(a)
    if side == "top":
        return int(xs[ys == ys.min()].mean()), int(ys.min())
    edge = xs.max() if side == "right" else xs.min()
    return int(edge), int(ys[xs == edge].mean())
