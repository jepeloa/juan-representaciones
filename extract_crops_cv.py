"""Render each PDF page and use OpenCV to find photo-like regions, save crops.

Strategy:
  * Render each page at 200dpi.
  * Compute local color variance — photos have high variance, text/background low.
  * Threshold + morphological close to merge nearby variance regions.
  * Extract bounding boxes large enough to be a product photo (≥ 150x150 px).
  * Save each crop as a JPG and append entries to the existing manifest.json
    with a 'source' field so the import/CLIP scripts can identify them.

The crops augment the embedded-image pool used by clip_match.py.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

ROOT = Path('/home/javier/juan')
BASE_PDFS = ROOT / 'Listas actualizadas'
OUT = ROOT / 'images'
MANIFEST = OUT / 'manifest.json'
DPI = 200
MAX_DIM = 320
JPEG_QUALITY = 78

# Tunables
VARIANCE_THRESHOLD = 600
MORPH_KERNEL = 35
MIN_AREA = 18000
MIN_DIM = 120
MAX_RATIO = 4.0

# We use the supplier mapping from extract_images.py
ROOT_FILE_SUPPLIER = {
    'CATALOGO DE PRODUCTOS MB.pdf': 'MB',
    'Cortadora BIANCHI NOVA  330.pdf': 'Bianchi',
    'FADECO enero26.pdf': 'Fadeco',
    'Lista precio ENERO 2026 RESINET.pdf': 'Resinet',
    'Picadoras y sierras.pdf': 'Asadores DEC',
    'Calefactores de exterior.pdf': 'Asadores DEC',
    'Mantenedores de calor.pdf': 'Asadores DEC',
    'Bandejas LGR.pdf': 'LGR',
    'Asadores 2026.pdf': 'Asadores DEC',
}


def supplier_for(pdf: Path) -> str:
    rel = pdf.relative_to(BASE_PDFS)
    parts = rel.parts
    if len(parts) >= 2:
        return parts[0]
    return ROOT_FILE_SUPPLIER.get(pdf.name, 'Otros')


def safe_id(s: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '_', s).strip('_')


def render_page(pdf_path: Path, page_idx: int, dpi: int = DPI) -> np.ndarray:
    """Render a 1-indexed PDF page as numpy RGB array."""
    doc = fitz.open(pdf_path)
    page = doc[page_idx - 1]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    doc.close()
    return arr  # RGB (alpha=False ensures 3 channels)


def find_regions(img_rgb: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Return list of (x, y, w, h) photo-like rects."""
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    f = gray.astype(np.float32)
    mean = cv2.boxFilter(f, -1, (21, 21))
    var = cv2.boxFilter(f * f, -1, (21, 21)) - mean * mean
    mask = (var > VARIANCE_THRESHOLD).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((MORPH_KERNEL, MORPH_KERNEL), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((10, 10), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rects = []
    H, W = img_rgb.shape[:2]
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w * h < MIN_AREA:
            continue
        if w < MIN_DIM or h < MIN_DIM:
            continue
        if max(w, h) / min(w, h) > MAX_RATIO:
            continue
        # Cover ≥ 85% of page → likely background image, skip
        if (w * h) / (W * H) > 0.85:
            continue
        # Padding to avoid clipping the border
        pad = 8
        x = max(0, x - pad); y = max(0, y - pad)
        w = min(W - x, w + 2*pad); h = min(H - y, h + 2*pad)
        rects.append((x, y, w, h))
    return rects


def save_crop(img_rgb: np.ndarray, rect, out_path: Path) -> tuple[int, int, dict]:
    x, y, w, h = rect
    crop = img_rgb[y:y+h, x:x+w]
    pim = Image.fromarray(crop)
    pim.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
    pim.save(out_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)
    # Color-richness check (already filtered by variance, but double-check)
    gray = pim.convert('L')
    hist = gray.histogram()
    nonzero = sum(1 for v in hist if v > 0)
    return pim.width, pim.height, {'colors': nonzero, 'is_flat': nonzero < 80}


def process_pdf(pdf_path: Path, manifest: dict) -> int:
    archivo = pdf_path.name
    supplier = supplier_for(pdf_path)
    out_dir = OUT / safe_id(supplier)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_prefix = safe_id(pdf_path.stem)
    entries = manifest.setdefault(archivo, [])
    try:
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        doc.close()
    except Exception as e:
        print(f'  skip {archivo}: {e}')
        return 0

    added = 0
    for page_idx in range(1, num_pages + 1):
        try:
            img = render_page(pdf_path, page_idx, DPI)
        except Exception:
            continue
        if img.shape[2] != 3:
            continue
        rects = find_regions(img)
        H, W = img.shape[:2]
        for ri, rect in enumerate(rects, start=1):
            fname = f'{safe_prefix}_p{page_idx:03d}_cv{ri:02d}.jpg'
            out_path = out_dir / fname
            w_out, h_out, extra = save_crop(img, rect, out_path)
            x, y, w, h = rect
            entry = {
                'page': page_idx,
                'idx': 900 + ri,  # to avoid collision with embedded image indices
                'src': f'images/{safe_id(supplier)}/{fname}',
                'w': w_out,
                'h': h_out,
                'colors': extra['colors'],
                'source': 'cv',
                'bbox': {
                    'x0': round(x / W, 4),
                    'y0': round(y / H, 4),
                    'x1': round((x + w) / W, 4),
                    'y1': round((y + h) / H, 4),
                    'cy': round((y + h / 2) / H, 4),
                },
            }
            if extra['is_flat']:
                entry['is_flat'] = True
            entries.append(entry)
            added += 1
    return added


def main():
    if not MANIFEST.exists():
        print(f'ERROR: {MANIFEST} not found. Run extract_images.py first.', file=__import__('sys').stderr)
        return
    manifest = json.loads(MANIFEST.read_text())
    # Remove previous CV crops from manifest (idempotent)
    for archivo in list(manifest.keys()):
        manifest[archivo] = [e for e in manifest[archivo] if e.get('source') != 'cv']

    pdfs = [p for p in BASE_PDFS.rglob('*.pdf') if not any(part.startswith('_') for part in p.relative_to(BASE_PDFS).parts)]
    print(f'Scanning {len(pdfs)} PDFs with OpenCV variance detection...')
    total = 0
    for pdf in sorted(pdfs):
        added = process_pdf(pdf, manifest)
        total += added
        print(f'  [{supplier_for(pdf):14}] {pdf.name}: +{added} CV crops')
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f'\nAdded {total} OpenCV crops. Manifest now has '
          f'{sum(len(v) for v in manifest.values())} entries.')


if __name__ == '__main__':
    main()
