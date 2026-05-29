"""CLIP-based product → image matching.

For each product in Catalogo_Consolidado.xlsx:
  - Compute multilingual text embedding (name + description + category)
  - Pool of candidate images = all images from the product's source file
    (filtered: no logos, no barcodes, reasonable aspect ratio)
  - Rank candidates by cosine similarity
  - Keep top-K above SIMILARITY_THRESHOLD

Output: clip_matches.json mapping {row_key: [image_src, ...]} where
row_key = f"{supplier}|{code or '_'}|{name}".

The import script reads this file to attach images, falling back to the
heuristic spatial matching for products without a CLIP match.
"""
from __future__ import annotations
import json
import os
from collections import defaultdict
from pathlib import Path

import openpyxl
import numpy as np
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer

ROOT = Path('/home/javier/juan')
XLSX = ROOT / 'Catalogo_Consolidado.xlsx'
MANIFEST = ROOT / 'images' / 'manifest.json'
OUT = ROOT / 'clip_matches.json'

# Multilingual CLIP: same embedding space as standard CLIP-ViT-B-32 but
# the text encoder handles Spanish properly.
IMG_MODEL = 'clip-ViT-B-32'
TEXT_MODEL = 'sentence-transformers/clip-ViT-B-32-multilingual-v1'

SIMILARITY_THRESHOLD = 0.20  # below this we trust nothing
TOP_K = 4                    # max images per product
BATCH_SIZE = 32

# Use CPU; this is fine for 1683 images
DEVICE = 'cpu'


def row_key(p: dict) -> str:
    sup = p.get('Proveedor') or ''
    code = p.get('Codigo') or '_'
    name = (p.get('Producto') or '')[:100]
    return f'{sup}|{code}|{name}'


def load_products() -> list[dict]:
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    ws = wb['Consolidado']
    headers = None
    rows = []
    for r in ws.iter_rows(values_only=True):
        if headers is None:
            headers = r
            continue
        if not any(r):
            continue
        d = dict(zip(headers, r))
        if d.get('Producto'):
            rows.append(d)
    wb.close()
    return rows


SUPPLIER_OF_FILE = {
    # Map archivo name → supplier name (mirrors extract_images.ROOT_FILE_SUPPLIER + folder convention)
    'CATALOGO DE PRODUCTOS MB.pdf': 'MB',
    'Cortadora BIANCHI NOVA  330.pdf': 'Bianchi',
    'FADECO enero26.pdf': 'Fadeco',
    'Lista precio ENERO 2026 RESINET.pdf': 'Resinet',
    'Picadoras y sierras.pdf': 'Asadores DEC',
    'Calefactores de exterior.pdf': 'Asadores DEC',
    'Mantenedores de calor.pdf': 'Asadores DEC',
    'Bandejas LGR.pdf': 'LGR',
    'Asadores 2026.pdf': 'Asadores DEC',
    'Catalogo Danda_2026.pdf': 'Danda',
    'Lista de Precios Marzo  2026.pdf': 'Danda',
    'AMASADORAS Y SOBADORAS MAYORISTA 01-05-26.pdf': 'Don Segura',
    'Don Segura.pdf': 'Don Segura',
    'LISTA BATEAS 01-05-2026.pdf': 'Don Segura',
    'LISTA DE PRECIOS MESAS Y PILETAS - 7-04-26.pdf': 'Don Segura',
    'CATALOGO_MAQUINARIA_DUNIA_ABRIL_2026.pdf': 'Dunia',
    'DUNIA-MAQUINARIAS - ABRIL.xlsx': 'Dunia',
    'FAM CATALOGO DIGITAL - HAVARD.pdf': 'Havard',
    'FAME HAVARD MARZO 2026.pdf': 'Havard',
    'GeloparAbril2026.pdf': 'Havard',
    'HavardMayorista MAYO 2026.pdf': 'Havard',
    'HavardMayorista-marzo-sinprecios.pdf': 'Havard',
    'LISTA MAYORISTA TRAMONTINA HAVARD.pdf': 'Havard',
    'Lista de precios Börgen - Marzo 2026 - USD.pdf': 'Havard',
    'PREVENTA CALEFACCION BORGEN 2026 -.pdf': 'Havard',
    'CATALOGO DF V.02.25.pdf': 'Turboblender',
    'Condición de pago Diciembre 2025.pdf': 'Turboblender',
    'LISTA DE PRECIOS DF V.01.26.pdf': 'Turboblender',
    'Lista Turboblender abril 26.pdf': 'Turboblender',
    'Catalogo ARE - Diciembre 2024.pdf': 'ARE',
    'PRECIOS.pdf': 'ARE',
    'LISTA DE PRECIOS DS CAMPANAS.pdf': 'DS Campanas',
}


def load_image_pool(manifest: dict) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Return (per_archivo_pool, per_supplier_pool)."""
    pool: dict[str, list[dict]] = {}
    pool_sup: dict[str, list[dict]] = {}
    for archivo, imgs in manifest.items():
        # Watermark detection: dims appearing >=3 pages → logo
        wh_pages: dict[tuple, set] = defaultdict(set)
        for im in imgs:
            wh_pages[(im['w'], im['h'])].add(im['page'])
        logo_dims = {wh for wh, pages in wh_pages.items() if len(pages) >= 3}

        good = []
        for im in imgs:
            if im.get('is_flat'):
                continue
            if (im['w'], im['h']) in logo_dims:
                continue
            if max(im['w'], im['h']) >= 2.5 * min(im['w'], im['h']):
                continue
            bb = im.get('bbox') or {}
            if bb:
                coverage = (bb.get('x1', 0) - bb.get('x0', 0)) * (bb.get('y1', 0) - bb.get('y0', 0))
                if coverage > 0.85:
                    continue
            good.append(im)
        if good:
            pool[archivo] = good
            sup = SUPPLIER_OF_FILE.get(archivo)
            if sup:
                pool_sup.setdefault(sup, []).extend(good)
    return pool, pool_sup


def main():
    print('Loading products + manifest...')
    products = load_products()
    manifest = json.loads(MANIFEST.read_text())
    pool, pool_sup = load_image_pool(manifest)

    print(f'Products: {len(products)}')
    print(f'Files with usable images: {len(pool)}')
    print(f'Total usable images: {sum(len(v) for v in pool.values())}')
    print(f'Suppliers with images: {len(pool_sup)}')

    print('Loading CLIP models (first run downloads ~600MB)...')
    img_model = SentenceTransformer(IMG_MODEL, device=DEVICE)
    text_model = SentenceTransformer(TEXT_MODEL, device=DEVICE)

    # ===== Encode all images =====
    print('Encoding images...')
    all_imgs = []
    src_to_idx = {}
    for archivo, imgs in pool.items():
        for im in imgs:
            src_to_idx[im['src']] = len(all_imgs)
            all_imgs.append(im)

    pil_imgs = []
    failed = 0
    for im in all_imgs:
        try:
            pil_imgs.append(Image.open(ROOT / im['src']).convert('RGB'))
        except Exception as e:
            print(f'  warn: cannot open {im["src"]}: {e}')
            pil_imgs.append(Image.new('RGB', (224, 224), 'white'))
            failed += 1

    img_embs = img_model.encode(
        pil_imgs, batch_size=BATCH_SIZE, show_progress_bar=True,
        convert_to_numpy=True, normalize_embeddings=True,
    )
    print(f'Image embeddings: shape={img_embs.shape}, failed={failed}')

    # ===== First-stage filter: reject crops that look like tables / text / charts =====
    print('Filtering tables/text/diagrams with CLIP zero-shot + color saturation...')
    POSITIVE_PROMPTS = [
        'a photo of a kitchen appliance',
        'a photo of a commercial refrigerator',
        'a photo of an industrial machine',
        'a photo of cookware or kitchenware',
        'a product photo on white background',
        'a photo of stainless steel equipment',
    ]
    NEGATIVE_PROMPTS = [
        'a table of prices and numbers',
        'a list of text and numbers',
        'a page of dense text',
        'a spreadsheet',
        'a barcode',
        'a logo',
        'a technical diagram with measurements',
        'a chart or graph',
        'a price list',
        'an invoice',
    ]
    pos_text = text_model.encode(POSITIVE_PROMPTS, convert_to_numpy=True, normalize_embeddings=True)
    neg_text = text_model.encode(NEGATIVE_PROMPTS, convert_to_numpy=True, normalize_embeddings=True)
    pos_scores = (img_embs @ pos_text.T).max(axis=1)
    neg_scores = (img_embs @ neg_text.T).max(axis=1)

    # Color-saturation check: tables/text are near-grayscale, photos have color.
    # Compute mean saturation per image.
    print('  computing color saturation...')
    saturations = np.zeros(len(pil_imgs), dtype=np.float32)
    for i, pim in enumerate(pil_imgs):
        try:
            hsv = pim.convert('HSV')
            arr = np.asarray(hsv)
            # Only count "non-white" pixels: v > 30 and v < 240 (avoids pure white/black noise)
            v = arr[..., 2]
            mask_v = (v > 30) & (v < 240)
            if mask_v.sum() == 0:
                saturations[i] = 0.0
            else:
                saturations[i] = arr[..., 1][mask_v].mean() / 255.0
        except Exception:
            saturations[i] = 1.0  # fail open

    # Composite filter:
    #   - pos_score > neg_score + 0.03 margin (more product-like than table-like)
    #   - pos_score absolute > 0.22 (must look at least somewhat like a product)
    #   - saturation > 0.06 (not nearly grayscale)
    photo_mask = (
        (pos_scores > neg_scores + 0.03)
        & (pos_scores > 0.22)
        & (saturations > 0.06)
    )
    n_kept = int(photo_mask.sum())
    n_dropped = len(photo_mask) - n_kept
    print(f'  kept {n_kept} photos, dropped {n_dropped} (tables/text/diagrams/grayscale)')

    # Apply the filter to the pool too — rebuild candidates lists
    for archivo in list(pool.keys()):
        kept = [im for im in pool[archivo] if photo_mask[src_to_idx[im['src']]]]
        if kept:
            pool[archivo] = kept
        else:
            del pool[archivo]
    for sup in list(pool_sup.keys()):
        kept = [im for im in pool_sup[sup] if photo_mask[src_to_idx[im['src']]]]
        if kept:
            pool_sup[sup] = kept
        else:
            del pool_sup[sup]

    # ===== Encode all product texts =====
    print('Encoding product texts...')
    texts = []
    for p in products:
        name = p.get('Producto') or ''
        desc = p.get('Descripcion') or ''
        cat = p.get('Categoria') or ''
        prompt = f'Foto de producto: {name}. {desc}. {cat}'.strip()
        texts.append(prompt)

    text_embs = text_model.encode(
        texts, batch_size=BATCH_SIZE, show_progress_bar=True,
        convert_to_numpy=True, normalize_embeddings=True,
    )
    print(f'Text embeddings: shape={text_embs.shape}')

    # ===== Per-product ranking =====
    print('Matching...')
    matches: dict[str, list[str]] = {}
    stats = {'with_match': 0, 'no_match': 0, 'no_pool': 0}
    sim_distribution = []
    for p, t_emb in zip(products, text_embs):
        archivo = (p.get('Archivo origen') or '').strip()
        sup = (p.get('Proveedor') or '').strip()
        candidates = pool.get(archivo, [])
        # Fallback: widen to all images of the same supplier if same-file is empty.
        if not candidates and sup in pool_sup:
            candidates = pool_sup[sup]
        if not candidates:
            stats['no_pool'] += 1
            continue
        # Get embeddings of candidates
        cand_indices = [src_to_idx[im['src']] for im in candidates]
        cand_embs = img_embs[cand_indices]
        sims = cand_embs @ t_emb  # cosine since both normalized
        ranked = sorted(zip(candidates, sims), key=lambda x: -x[1])
        # Keep top-K above threshold
        top = [(im, sim) for im, sim in ranked[:TOP_K] if sim >= SIMILARITY_THRESHOLD]
        if top:
            matches[row_key(p)] = [im['src'] for im, _ in top]
            stats['with_match'] += 1
            sim_distribution.append(float(top[0][1]))
        else:
            stats['no_match'] += 1
            # For debugging: see what was the best similarity
            if ranked:
                sim_distribution.append(float(ranked[0][1]))

    print(f'\n=== Match results ===')
    print(f'  Products with CLIP match: {stats["with_match"]}')
    print(f'  Below threshold:          {stats["no_match"]}')
    print(f'  No images in source file: {stats["no_pool"]}')
    if sim_distribution:
        sims_arr = np.array(sim_distribution)
        print(f'  Top-sim distribution: min={sims_arr.min():.3f} p25={np.percentile(sims_arr, 25):.3f} '
              f'med={np.median(sims_arr):.3f} p75={np.percentile(sims_arr, 75):.3f} max={sims_arr.max():.3f}')

    OUT.write_text(json.dumps(matches, indent=2, ensure_ascii=False))
    print(f'\nWrote {OUT} ({len(matches)} products)')


if __name__ == '__main__':
    main()
