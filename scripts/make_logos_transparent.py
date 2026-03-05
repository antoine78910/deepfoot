#!/usr/bin/env python3
"""
Rend le fond noir des logos PNG transparent.
Usage: depuis la racine du repo: python scripts/make_logos_transparent.py
"""
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow")
    raise

LP_LOGOS = Path(__file__).resolve().parent.parent / "frontend" / "public" / "lp-logos"
THRESHOLD = 35  # pixels with R,G,B <= this become transparent


def main():
    if not LP_LOGOS.is_dir():
        print(f"Not found: {LP_LOGOS}")
        return
    for i in range(1, 27):
        p = LP_LOGOS / f"logo-{i}.png"
        if not p.exists():
            continue
        img = Image.open(p).convert("RGBA")
        data = img.getdata()
        out = []
        for (r, g, b, a) in data:
            if r <= THRESHOLD and g <= THRESHOLD and b <= THRESHOLD:
                out.append((r, g, b, 0))
            else:
                out.append((r, g, b, a))
        img.putdata(out)
        img.save(p, "PNG")
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
