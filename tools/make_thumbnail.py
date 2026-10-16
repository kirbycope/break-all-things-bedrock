"""Build the 1920x1080 thumbnail for YouTube and Planet Minecraft, and the 960x540 repository preview.

Everything it needs is committed: the birch glade from the trailer in assets/background.png, the diamond vein
breaking in assets/vein.png, the player skin in assets/skin.png, the Timber Axe texture and Bangers in tools/fonts/.
The title, cards and grading come from thumbnail_kit.py, the thumbnail skill's shared half.

    python tools/make_thumbnail.py
    python tools/make_thumbnail.py --no-preview
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from PIL import Image, ImageFilter

import skin_render
from thumbnail_kit import H, W, WHITE, Title, card, far_point, grade, outline, patch_out, vignette

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TITLE = Title(
    font=os.path.join(HERE, "fonts", "Bangers-Regular.ttf"),
    styles={
        "white": WHITE,
        # the meme's own colours: the yellow burst and the hot pink shirt
        "burst": dict(top=(255, 250, 120), bot=(255, 206, 0), side=(178, 112, 0)),
        "pink":  dict(top=(255, 120, 206), bot=(232, 0, 132), side=(122, 0, 68)),
    },
    lines=[
        dict(text="BREAK ALL", style="burst", cap=168, arc=7),
        dict(text="THE THINGS!", style="pink", cap=168, arc=7),
        dict(text="BEDROCK", style="white", cap=104, arc=-10),
    ],
)

AXE = os.path.join(ROOT, "development_resource_packs", "break_all_things", "textures", "items", "timber_axe.png")
VEIN_CROP = (300, 60, 1740, 870)      # the hole, the diamonds in the air and the lapis left standing
STEVE_BOX = (840, 450, 1100, 1030)    # the player the trailer filmed, painted out of the plate
AXE_AT = (-80, 70)                    # the grip, a little up the handle from its end, at the hand


def build() -> Image.Image:
    plate = Image.open(os.path.join(ROOT, "assets", "background.png")).convert("RGB")

    # the glade behind, softened and pushed back so the title and the card carry
    backdrop = patch_out(plate, STEVE_BOX).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.4))
    canvas = grade(backdrop, sat=1.34, contrast=1.08, bright=0.97).convert("RGBA")

    # the vein the moment it breaks, lifted out on a card
    vein = Image.open(os.path.join(ROOT, "assets", "vein.png")).convert("RGB").crop(VEIN_CROP)
    vein = grade(vein.resize((800, int(800 * vein.height / vein.width)), Image.LANCZOS), sat=1.3, contrast=1.12, bright=1.12)
    canvas.alpha_composite(card(vein).rotate(3, expand=True, resample=Image.BICUBIC), (1030, 420))

    # the player, big in the corner, holding the Timber Axe out toward the vein
    swing = {
        "head":      (-6, 24, 0),
        "body":      (0, 10, 0),
        "arm_right": (-4, 0, -9),
        "arm_left":  (-80, 0, 34),
        "leg_right": (7, 0, -7),
        "leg_left":  (-8, 0, 8),
    }
    char = skin_render.render(os.path.join(ROOT, "assets", "skin.png"), height=820, yaw=24, pitch=3, outline=11, pose=swing)
    char_pos = (560, H - char.height + 250)
    canvas.alpha_composite(char, char_pos)

    # the axe drawn after the player, so it sits in the hand rather than behind it; reflected across the handle
    # (TRANSVERSE), so the handle still runs bottom left to top right and the blade faces forward, toward the vein
    hx, hy = far_point(char, "right")
    axe = outline(Image.open(AXE).convert("RGBA").transpose(Image.Transpose.TRANSVERSE).resize((360, 360), Image.NEAREST))
    canvas.alpha_composite(axe, (char_pos[0] + hx + AXE_AT[0], char_pos[1] + hy - axe.height + AXE_AT[1]))

    block, at = TITLE.place(86, 74, tilt=-2.0)
    canvas.alpha_composite(block, at)

    return grade(vignette(canvas.convert("RGB"), 0.28), sat=1.06, contrast=1.04, bright=1.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "thumbnail.png"))
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    img = build()
    img.save(args.out)
    print(f"wrote {args.out} {img.size[0]}x{img.size[1]}")
    if not args.no_preview:
        # the repository preview is 960x540, written by the project's own tool
        subprocess.check_call([sys.executable, os.path.join(HERE, "make_preview.py"), args.out,
                               os.path.join(ROOT, "break-all-things-bedrock.png")])


if __name__ == "__main__":
    main()
