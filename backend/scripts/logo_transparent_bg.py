"""
Rend le fond noir du logo DEEPFOOT transparent.
Usage: python scripts/logo_transparent_bg.py
"""
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Installation de Pillow: pip install Pillow")
    raise

# Chemins (depuis la racine du backend)
ROOT = Path(__file__).resolve().parent.parent.parent
LOGO_PATH = ROOT / "frontend" / "public" / "logo.png"
OUT_PATH = ROOT / "frontend" / "public" / "logo.png"

# Seuil: pixels avec R,G,B <= THRESHOLD deviennent transparents
THRESHOLD = 40


def main():
    if not LOGO_PATH.exists():
        print(f"Fichier introuvable: {LOGO_PATH}")
        return
    img = Image.open(LOGO_PATH).convert("RGBA")
    data = img.getdata()
    new_data = []
    for item in data:
        r, g, b, a = item
        if r <= THRESHOLD and g <= THRESHOLD and b <= THRESHOLD:
            new_data.append((r, g, b, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    img.save(OUT_PATH, "PNG")
    print(f"Logo sauvegardé avec fond transparent: {OUT_PATH}")


if __name__ == "__main__":
    main()
