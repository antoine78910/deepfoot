"""Make logo background transparent (black/dark pixels -> alpha 0)."""
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow")
    raise

logo_path = Path(__file__).resolve().parent.parent / "public" / "logo.png"
img = Image.open(logo_path)
img = img.convert("RGBA")
data = img.getdata()
threshold = 30  # pixels with R,G,B all below this become transparent
new_data = []
for item in data:
    r, g, b, a = item
    if r <= threshold and g <= threshold and b <= threshold:
        new_data.append((r, g, b, 0))
    else:
        new_data.append(item)
img.putdata(new_data)
img.save(logo_path, "PNG")
print("Saved", logo_path)
