#!/usr/bin/env python3
"""
etch_blur.py — blur sensitive regions of a photo while etching a crisp edge
around Eli's body (or any person in the frame).

The privacy tool for The Archive: screens, boards, and rosters get frosted;
the person stays sharp to the pixel, because the mask is cut from a real
person-segmentation matte, not a rectangle.

Modes
-----
auto (default)  : uses rembg person segmentation to find the person, then
                  blurs everything you asked to blur EXCEPT the person.
polygon         : no ML — you supply the person outline as polygon points
                  in a JSON file; same etching logic.

Usage
-----
  # frost the whole background, keep the person etched sharp
  python3 etch_blur.py photo.jpg out.jpg --all-background

  # frost only given rectangles (fractions of width/height), person etched out
  python3 etch_blur.py photo.jpg out.jpg --region .03,.06,.70,.475

  # extra soft-blur ellipses (e.g. a child's face): fractions x0,y0,x1,y1
  python3 etch_blur.py photo.jpg out.jpg --region .03,.06,.70,.475 \
      --face .36,.55,.50,.64 --face .74,.29,.86,.38

  # polygon mode (points file: JSON [[x,y],...] in pixel coords)
  python3 etch_blur.py photo.jpg out.jpg --all-background --person-poly person.json

Options
-------
  --radius N        frost blur strength (default 13)
  --face-radius N   face soften strength (default 9)
  --feather N       mask feather in px (default 24)
  --maxw N          resize output to max width (default 1400; 0 = keep size)
  --keep-meta       skip the EXIF/GPS strip (default: strip everything)
"""
import argparse, json, os, sys
from PIL import Image, ImageOps, ImageFilter, ImageDraw


def person_mask_auto(im):
    try:
        from rembg import remove
    except ImportError:
        sys.exit("rembg not installed — `pip3 install rembg onnxruntime` or use --person-poly")
    cut = remove(im)               # RGBA with person alpha
    return cut.split()[-1]         # alpha channel as L mask


def person_mask_poly(im, path):
    pts = [tuple(p) for p in json.load(open(path))]
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def frac_box(spec, W, H):
    x0, y0, x1, y1 = (float(v) for v in spec.split(","))
    return (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--region", action="append", default=[],
                    help="x0,y0,x1,y1 fractions to frost (repeatable)")
    ap.add_argument("--all-background", action="store_true")
    ap.add_argument("--face", action="append", default=[],
                    help="x0,y0,x1,y1 fractions: soft ellipse blur (repeatable)")
    ap.add_argument("--person-poly", help="JSON polygon file -> polygon mode")
    ap.add_argument("--radius", type=int, default=13)
    ap.add_argument("--face-radius", type=int, default=9)
    ap.add_argument("--feather", type=int, default=24)
    ap.add_argument("--maxw", type=int, default=1400)
    ap.add_argument("--keep-meta", action="store_true")
    a = ap.parse_args()

    im = ImageOps.exif_transpose(Image.open(a.src)).convert("RGB")
    if a.maxw and im.width > a.maxw:
        im = im.resize((a.maxw, int(im.height * a.maxw / im.width)), Image.LANCZOS)
    W, H = im.size

    person = (person_mask_poly(im, a.person_poly) if a.person_poly
              else person_mask_auto(im))
    # harden + slightly grow the person matte so the etch hugs the body
    person = person.point(lambda v: 255 if v > 96 else 0)
    person = person.filter(ImageFilter.MaxFilter(9))

    # what to frost
    frost_mask = Image.new("L", (W, H), 255 if a.all_background else 0)
    d = ImageDraw.Draw(frost_mask)
    for spec in a.region:
        d.rectangle(frac_box(spec, W, H), fill=255)
    # etch the person OUT of the frost
    frost_mask.paste(0, (0, 0), person)
    frost_mask = frost_mask.filter(ImageFilter.GaussianBlur(a.feather))
    # re-cut the person after feathering so the body edge stays crisp
    frost_mask.paste(0, (0, 0), person.filter(ImageFilter.GaussianBlur(3)))

    out = Image.composite(im.filter(ImageFilter.GaussianBlur(a.radius)), im, frost_mask)

    # face softening (applies on top; not etched, faces are the point)
    if a.face:
        fm = Image.new("L", (W, H), 0)
        fd = ImageDraw.Draw(fm)
        for spec in a.face:
            fd.ellipse(frac_box(spec, W, H), fill=255)
        fm = fm.filter(ImageFilter.GaussianBlur(12))
        out = Image.composite(im.filter(ImageFilter.GaussianBlur(a.face_radius)), out, fm)

    if a.keep_meta:
        out.save(a.dst, "JPEG", quality=88, optimize=True)
    else:
        clean = Image.new(out.mode, out.size)
        clean.paste(out)
        clean.save(a.dst, "JPEG", quality=88, optimize=True)
    print("wrote", a.dst, out.size, f"{os.path.getsize(a.dst)//1024}KB")


if __name__ == "__main__":
    main()
