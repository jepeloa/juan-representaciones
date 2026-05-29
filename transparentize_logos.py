"""Strip near-white background from the JMG logos so they blend with cream panels."""
from PIL import Image
from pathlib import Path

SRC_DIR = Path('/home/javier/juan/media')
OUT_DIR = Path('/home/javier/juan/catalogo-app/frontend/public')

# (source, destination, threshold)
JOBS = [
    ('logo_juan.png', 'logo_login.png', 235),
    ('logo_solo.png', 'logo.png', 235),
]


def transparentize(src: Path, dst: Path, white_threshold: int):
    img = Image.open(src).convert('RGBA')
    data = img.getdata()
    new = []
    for r, g, b, a in data:
        if r >= white_threshold and g >= white_threshold and b >= white_threshold:
            # Make near-white fully transparent
            new.append((255, 255, 255, 0))
        else:
            # Slightly fade the alpha near very-light grays for smoother edges
            min_rgb = min(r, g, b)
            if min_rgb >= 200:
                # Linear ramp 200-235 → alpha 255-0
                alpha = int(((white_threshold - min_rgb) / (white_threshold - 200)) * 255)
                alpha = max(0, min(255, alpha))
                new.append((r, g, b, min(a, alpha)))
            else:
                new.append((r, g, b, a))
    img.putdata(new)
    img.save(dst, 'PNG', optimize=True)
    print(f'  {src.name} ({src.stat().st_size//1024} KB) → {dst.name} ({dst.stat().st_size//1024} KB)')


def main():
    for src, dst, t in JOBS:
        src_path = SRC_DIR / src
        dst_path = OUT_DIR / dst
        if not src_path.exists():
            print(f'  skip: {src_path} not found')
            continue
        transparentize(src_path, dst_path, t)


if __name__ == '__main__':
    main()
