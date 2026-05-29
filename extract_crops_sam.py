"""Use SAM to find product photo regions in PDF pages.

Strategy:
  * Identify pages that have products without photo (or with weak match).
  * Render those pages at 150dpi.
  * Run SAM AutomaticMaskGenerator → ~30 masks per page.
  * Filter masks: min size, max page-coverage, aspect ratio, saturation.
  * Save each surviving region as a JPG and add to manifest with source='sam'.

CLIP filter (in clip_match.py) will further reject tables/text.
"""
from __future__ import annotations
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import fitz
import numpy as np
import openpyxl
import torch
from PIL import Image
from segment_anything import SamAutomaticMaskGenerator, sam_model_registry

ROOT = Path('/home/javier/juan')
BASE_PDFS = ROOT / 'Listas actualizadas'
OUT = ROOT / 'images'
MANIFEST = OUT / 'manifest.json'
XLSX = ROOT / 'Catalogo_Consolidado.xlsx'
SAM_CHECKPOINT = ROOT / 'sam_models' / 'sam_vit_b_01ec64.pth'

# Run SAM at lower DPI to keep speed reasonable on CPU
DPI = 130
MAX_DIM = 320
JPEG_QUALITY = 78
MIN_AREA = 18000
MIN_DIM = 110
MAX_COVERAGE = 0.65
MAX_RATIO = 5.0

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
    doc = fitz.open(pdf_path)
    page = doc[page_idx - 1]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    doc.close()
    return arr  # RGB


def saturation_of(img_bgr: np.ndarray) -> float:
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    s = hsv[..., 1]
    v = hsv[..., 2]
    mask = (v > 30) & (v < 240)
    if mask.sum() == 0:
        return 0.0
    return float(s[mask].mean()) / 255.0


def pages_to_process() -> dict[str, set[int]]:
    """Return {archivo: {page numbers}} of pages where products live.

    We only run SAM on pages that actually have products (saves compute).
    """
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    ws = wb['Consolidado']
    headers = None
    out: dict[str, set[int]] = defaultdict(set)
    for r in ws.iter_rows(values_only=True):
        if headers is None:
            headers = r
            continue
        if not any(r):
            continue
        d = dict(zip(headers, r))
        a = d.get('Archivo origen')
        p = d.get('Pagina PDF')
        if a and p:
            try:
                out[a].add(int(p))
            except (TypeError, ValueError):
                pass
    wb.close()
    return out


def main():
    if not MANIFEST.exists():
        print(f'ERROR: {MANIFEST} not found.', file=sys.stderr)
        return

    print(f'Loading SAM ViT-B from {SAM_CHECKPOINT}...')
    sam = sam_model_registry['vit_b'](checkpoint=str(SAM_CHECKPOINT))
    sam.to(device='cpu')
    sam.eval()
    mask_gen = SamAutomaticMaskGenerator(
        sam,
        points_per_side=24,            # fewer points → faster, still good for product detection
        pred_iou_thresh=0.86,
        stability_score_thresh=0.85,
        crop_n_layers=0,
        min_mask_region_area=MIN_AREA // 4,
    )
    print('SAM loaded.')

    manifest = json.loads(MANIFEST.read_text())
    # Resume support: keep already-processed SAM entries; we'll skip pages that
    # already have any SAM entries.
    already_processed: set[tuple[str, int]] = set()
    for archivo, ents in manifest.items():
        for e in ents:
            if e.get('source') == 'sam':
                already_processed.add((archivo, int(e['page'])))

    pages_per_file = pages_to_process()
    pdfs_to_process = []
    for pdf in BASE_PDFS.rglob('*.pdf'):
        if any(part.startswith('_') for part in pdf.relative_to(BASE_PDFS).parts):
            continue
        archivo = pdf.name
        if archivo in pages_per_file:
            pdfs_to_process.append(pdf)

    total_pages = sum(len(pages_per_file[p.name]) for p in pdfs_to_process)
    print(f'Will process {total_pages} pages across {len(pdfs_to_process)} PDFs.')

    total_crops = 0
    page_count = 0
    for pdf in sorted(pdfs_to_process):
        archivo = pdf.name
        supplier = supplier_for(pdf)
        out_dir = OUT / safe_id(supplier)
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_prefix = safe_id(pdf.stem)
        file_entries = manifest.setdefault(archivo, [])

        pages = sorted(pages_per_file[archivo])
        for page_idx in pages:
            page_count += 1
            if (archivo, page_idx) in already_processed:
                print(f'  [{page_count}/{total_pages}] skip {archivo} p{page_idx} (already done)')
                continue
            try:
                rgb = render_page(pdf, page_idx, DPI)
            except Exception as e:
                print(f'  [{archivo} p{page_idx}] render fail: {e}')
                continue
            if rgb.shape[2] != 3:
                continue
            H, W = rgb.shape[:2]

            print(f'  [{page_count}/{total_pages}] SAM on {archivo} p{page_idx}...', flush=True)
            with torch.no_grad():
                try:
                    masks = mask_gen.generate(rgb)
                except Exception as e:
                    print(f'    SAM error: {e}')
                    continue

            added = 0
            seen_bboxes = []
            for m in masks:
                x, y, w, h = (int(v) for v in m['bbox'])
                area = w * h
                if area < MIN_AREA: continue
                if w < MIN_DIM or h < MIN_DIM: continue
                if area > W * H * MAX_COVERAGE: continue
                if min(w, h) == 0: continue
                if max(w, h) / min(w, h) > MAX_RATIO: continue

                # Dedup: skip near-duplicate bboxes
                cx = x + w / 2; cy_box = y + h / 2
                dup = False
                for px, py, pw, ph in seen_bboxes:
                    if abs(cx - (px + pw / 2)) < 30 and abs(cy_box - (py + ph / 2)) < 30 and abs(w - pw) < 40 and abs(h - ph) < 40:
                        dup = True
                        break
                if dup: continue

                # Pad slightly
                pad = 6
                x2 = max(0, x - pad); y2 = max(0, y - pad)
                w2 = min(W - x2, w + 2*pad); h2 = min(H - y2, h + 2*pad)
                crop_rgb = rgb[y2:y2+h2, x2:x2+w2]

                # Skip near-monochrome crops fast (saturation)
                crop_bgr = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2BGR)
                if saturation_of(crop_bgr) < 0.05:
                    continue

                pim = Image.fromarray(crop_rgb)
                pim.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
                gray = pim.convert('L')
                hist = gray.histogram()
                nonzero = sum(1 for v in hist if v > 0)

                added += 1
                fname = f'{safe_prefix}_p{page_idx:03d}_sam{added:02d}.jpg'
                out_path = out_dir / fname
                pim.save(out_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)
                entry = {
                    'page': page_idx,
                    'idx': 800 + added,
                    'src': f'images/{safe_id(supplier)}/{fname}',
                    'w': pim.width, 'h': pim.height,
                    'colors': nonzero,
                    'source': 'sam',
                    'bbox': {
                        'x0': round(x2 / W, 4), 'y0': round(y2 / H, 4),
                        'x1': round((x2 + w2) / W, 4), 'y1': round((y2 + h2) / H, 4),
                        'cy': round((y2 + h2 / 2) / H, 4),
                    },
                }
                if nonzero < 80:
                    entry['is_flat'] = True
                file_entries.append(entry)
                seen_bboxes.append((x, y, w, h))

            total_crops += added
            print(f'    +{added} crops')
            # Save manifest after each page to preserve progress on crash
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f'\nSAM done. Added {total_crops} crops. Manifest entries: {sum(len(v) for v in manifest.values())}')


if __name__ == '__main__':
    main()
