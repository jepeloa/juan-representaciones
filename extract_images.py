#!/usr/bin/env python3
"""Extract product images from supplier PDFs.

Walks every PDF under /home/javier/juan/Listas actualizadas/, pulls all embedded
images via PyMuPDF, resizes to a 320x320 max thumbnail and saves under
/home/javier/juan/images/<supplier>/<archivo>_pNN_iMM.jpg.

Generates images/manifest.json mapping each (archivo_origen, page) to the list of
thumbnails for that page, so build_html.py can attach a thumbnail to each product row.
"""
from __future__ import annotations
import io
import json
import re
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

BASE = Path('/home/javier/juan/Listas actualizadas')
OUT = Path('/home/javier/juan/images')
MIN_DIM = 80          # skip logos/icons smaller than this in any dimension
MAX_DIM = 320         # thumbnail size
JPEG_QUALITY = 75

# Supplier inferred from top-level folder under BASE. Loose-leaf PDFs in BASE root use a fallback.
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
    rel = pdf.relative_to(BASE)
    parts = rel.parts
    if len(parts) >= 2:
        return parts[0]
    return ROOT_FILE_SUPPLIER.get(pdf.name, 'Otros')


def safe_id(s: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '_', s).strip('_')


def extract_pdf_images(pdf_path: Path, supplier: str, manifest: dict):
    """Extract images from `pdf_path` into OUT/<supplier>/."""
    archivo = pdf_path.name
    out_dir = OUT / safe_id(supplier)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f'  [open-fail] {pdf_path.name}: {e}')
        return
    file_entries = manifest.setdefault(archivo, [])
    safe_prefix = safe_id(pdf_path.stem)
    for page_idx, page in enumerate(doc, start=1):
        try:
            images = page.get_images(full=True)
        except Exception:
            continue
        # Page dimensions to normalize bbox coords (0..1)
        page_w = float(page.rect.width) if page.rect.width else 1.0
        page_h = float(page.rect.height) if page.rect.height else 1.0
        for img_idx, img in enumerate(images, start=1):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:  # CMYK
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                img_bytes = pix.tobytes('png')
                pim = Image.open(io.BytesIO(img_bytes)).convert('RGB')
            except Exception as e:
                continue
            w, h = pim.size
            if min(w, h) < MIN_DIM:
                continue  # skip small icons/logos
            # Find where on the page this image is placed (may have multiple rects;
            # use the first one).
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []
            bbox = None
            if rects:
                r = rects[0]
                bbox = {
                    'x0': round(r.x0 / page_w, 4),
                    'y0': round(r.y0 / page_h, 4),
                    'x1': round(r.x1 / page_w, 4),
                    'y1': round(r.y1 / page_h, 4),
                    # Center y for easy ranking
                    'cy': round((r.y0 + r.y1) / (2 * page_h), 4),
                }
            pim.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
            # Heuristic for barcodes / text-bitmap detection:
            # Real product photos have thousands of distinct grayscale values; barcodes
            # and embedded text bitmaps have very few (mostly pure black + pure white).
            try:
                gray = pim.convert('L')
                hist = gray.histogram()
                nonzero_bins = sum(1 for v in hist if v > 0)
                # Fraction of pixels at the extremes (very dark + very bright)
                total = gray.width * gray.height
                extreme = sum(hist[i] for i in range(0, 30)) + sum(hist[i] for i in range(225, 256))
                extreme_ratio = extreme / total if total else 0
            except Exception:
                nonzero_bins = 256
                extreme_ratio = 0
            # Barcodes / text bitmaps have either very few unique gray levels OR
            # the vast majority of pixels at the extremes (black/white).
            is_barcode_or_text = nonzero_bins < 80 or extreme_ratio > 0.85
            fname = f'{safe_prefix}_p{page_idx:03d}_i{img_idx:02d}.jpg'
            out_path = out_dir / fname
            pim.save(out_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)
            entry = {
                'page': page_idx,
                'idx': img_idx,
                'src': f'images/{safe_id(supplier)}/{fname}',
                'w': pim.width,
                'h': pim.height,
                'colors': nonzero_bins,
            }
            if is_barcode_or_text:
                entry['is_flat'] = True  # binary / barcode / text bitmap
            if bbox:
                entry['bbox'] = bbox
            file_entries.append(entry)
    doc.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    pdfs = [p for p in BASE.rglob('*.pdf') if not any(part.startswith('_') for part in p.relative_to(BASE).parts)]
    print(f'Scanning {len(pdfs)} PDFs...')
    for pdf in sorted(pdfs):
        supplier = supplier_for(pdf)
        before = len(manifest.get(pdf.name, []))
        extract_pdf_images(pdf, supplier, manifest)
        added = len(manifest.get(pdf.name, [])) - before
        print(f'  [{supplier}] {pdf.name}: +{added} images')
    manifest_path = OUT / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    total = sum(len(v) for v in manifest.values())
    print(f'TOTAL: {total} thumbnails across {len(manifest)} files. Wrote {manifest_path}')


if __name__ == '__main__':
    main()
