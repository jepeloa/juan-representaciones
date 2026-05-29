"""Import the consolidated Excel + image manifest into MySQL.

Image matching strategy (in order of preference):
    1. CLIP matches (clip_matches.json) — multilingual text-to-image similarity.
       Used when row_key (supplier|code|name) is present in the file.
    2. Spatial heuristic — products grouped by (archivo, page), images
       distributed in cy-sorted chunks.

If neither matches, the product is saved without images.
"""
from __future__ import annotations
import json
import re
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

import openpyxl
from sqlalchemy import select

sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import Supplier, Category, Product, ProductImage


def slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def to_decimal(v) -> Decimal | None:
    if v is None or v == '':
        return None
    try:
        return Decimal(str(v)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return None


def load_excel(xlsx_path: Path) -> Iterable[dict]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb['Consolidado']
    headers = None
    for r in ws.iter_rows(values_only=True):
        if headers is None:
            headers = [str(v or '').strip() for v in r]
            continue
        if not any(r):
            continue
        yield {h: v for h, v in zip(headers, r)}
    wb.close()


def build_page_pools(manifest: dict) -> dict[tuple[str, int], list[dict]]:
    """For each (archivo, page), return a list of image entries (filtered),
    sorted by center-Y ascending (top to bottom).
    """
    pools: dict[tuple[str, int], list[dict]] = {}
    for archivo, imgs in manifest.items():
        # Watermark detection: (w,h) appearing on >=3 pages → logo
        wh_pages: dict[tuple[int, int], set[int]] = defaultdict(set)
        for img in imgs:
            p = img.get('page')
            w = img.get('w', 0)
            h = img.get('h', 0)
            if p is None:
                continue
            wh_pages[(w, h)].add(int(p))
        logo_dims = {wh for wh, pages_seen in wh_pages.items() if len(pages_seen) >= 3}

        by_page: dict[int, list[dict]] = defaultdict(list)
        for img in imgs:
            page = img.get('page')
            if page is None:
                continue
            w = img.get('w', 0)
            h = img.get('h', 0)
            if w < 60 or h < 60:
                continue
            if (w, h) in logo_dims:
                continue
            # Skip barcodes / embedded text bitmaps (few unique grayscale values).
            if img.get('is_flat'):
                continue
            # Reject extreme aspect ratios — banners, dividers.
            if max(w, h) >= 2.5 * min(w, h):
                continue
            # Skip image that occupies full page (background watermark/cover)
            bbox = img.get('bbox') or {}
            if bbox:
                page_coverage = (bbox.get('x1', 0) - bbox.get('x0', 0)) * (bbox.get('y1', 0) - bbox.get('y0', 0))
                if page_coverage > 0.85:
                    continue
            by_page[int(page)].append(img)

        for page, page_imgs in by_page.items():
            # Sort by center Y; fall back to idx
            page_imgs.sort(key=lambda x: (
                (x.get('bbox') or {}).get('cy', 0.5),
                x.get('idx', 0),
            ))
            pools[(archivo, page)] = page_imgs
    return pools


def distribute_images(images: list[dict], num_products: int) -> list[list[str]]:
    """Given a sorted-by-cy list of M images and N products, return a list of N
    image-source lists, one per product.

    Strategy: split the sorted-by-cy image list into N consecutive chunks. The
    i-th product gets the i-th chunk. This guarantees every image is assigned
    (no orphans) and that the order roughly tracks the page's top-to-bottom flow.

    Examples:
      M=3, N=1 → product 0 gets all 3
      M=3, N=2 → product 0 gets [0,1], product 1 gets [2]
      M=6, N=3 → each product gets 2
      M=2, N=3 → product 0 gets [0], product 1 gets [1], product 2 gets nothing
    """
    if not images or num_products <= 0:
        return [[] for _ in range(max(num_products, 1))]
    if num_products == 1:
        return [[im['src'] for im in images]]
    M = len(images)
    N = num_products
    buckets: list[list[str]] = [[] for _ in range(N)]
    for i, im in enumerate(images):
        bucket_idx = min(N - 1, (i * N) // M)
        buckets[bucket_idx].append(im['src'])
    return buckets


def row_key(supplier: str, code: str | None, name: str) -> str:
    return f'{supplier}|{code or "_"}|{name[:100]}'


def main():
    if len(sys.argv) < 3:
        print('usage: python scripts/import_excel.py <xlsx> <manifest.json> [<clip_matches.json>]', file=sys.stderr)
        sys.exit(2)

    xlsx_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])
    clip_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    if not xlsx_path.exists():
        print(f'ERROR: {xlsx_path} no existe', file=sys.stderr)
        sys.exit(1)

    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    print(f'Excel: {xlsx_path}, manifest: {len(manifest)} archivos')

    clip_matches: dict[str, list[str]] = {}
    if clip_path and clip_path.exists():
        clip_matches = json.loads(clip_path.read_text(encoding='utf-8'))
        print(f'CLIP matches: {len(clip_matches)} products')

    # Read all rows first to group by (archivo, page)
    all_rows = list(load_excel(xlsx_path))
    print(f'Rows in Excel: {len(all_rows)}')

    # Group products by (archivo, page) preserving the order of appearance in Excel
    grouped: dict[tuple[str, int], list[int]] = defaultdict(list)
    for idx, r in enumerate(all_rows):
        archivo = (r.get('Archivo origen') or '').strip()
        page = r.get('Pagina PDF')
        if archivo and page is not None:
            try:
                grouped[(archivo, int(page))].append(idx)
            except (TypeError, ValueError):
                pass

    pools = build_page_pools(manifest)

    # Precompute image lists per row index
    images_for_row: dict[int, list[str]] = {}
    for (archivo, page), row_indices in grouped.items():
        page_imgs = pools.get((archivo, page), [])
        buckets = distribute_images(page_imgs, len(row_indices))
        for ri, srcs in zip(row_indices, buckets):
            images_for_row[ri] = srcs

    db = SessionLocal()
    try:
        # Clear existing data (idempotent re-import)
        db.query(ProductImage).delete()
        db.query(Product).delete()
        db.query(Category).delete()
        db.query(Supplier).delete()
        db.commit()

        sup_cache: dict[str, Supplier] = {}
        cat_cache: dict[tuple[int, str], Category] = {}

        inserted = 0
        no_image_count = 0
        with_image_count = 0
        total_images_attached = 0
        for idx, r in enumerate(all_rows):
            sup_name = (r.get('Proveedor') or '').strip()
            if not sup_name:
                continue
            name = (r.get('Producto') or '').strip()
            if not name:
                continue

            if sup_name not in sup_cache:
                sup = db.execute(select(Supplier).where(Supplier.name == sup_name)).scalar_one_or_none()
                if not sup:
                    sup = Supplier(name=sup_name, slug=slug(sup_name))
                    db.add(sup)
                    db.flush()
                sup_cache[sup_name] = sup
            sup = sup_cache[sup_name]

            cat_name = (r.get('Categoria') or '').strip() or None
            cat = None
            if cat_name:
                key = (sup.id, cat_name)
                if key not in cat_cache:
                    cat = db.execute(
                        select(Category).where(Category.supplier_id == sup.id, Category.name == cat_name)
                    ).scalar_one_or_none()
                    if not cat:
                        cat = Category(supplier_id=sup.id, name=cat_name)
                        db.add(cat)
                        db.flush()
                    cat_cache[key] = cat
                cat = cat_cache[key]

            archivo = (r.get('Archivo origen') or '').strip() or None
            iva_raw = r.get('IVA')
            iva = None if iva_raw is None else str(iva_raw)
            bulto = r.get('Cantidad x Bulto')
            try:
                bulto = int(bulto) if bulto not in (None, '') else None
            except (TypeError, ValueError):
                bulto = None

            product = Product(
                supplier_id=sup.id,
                category_id=cat.id if cat else None,
                code=(str(r.get('Codigo')).strip() if r.get('Codigo') else None),
                name=name[:500],
                description=(r.get('Descripcion') or None),
                price=to_decimal(r.get('Precio')),
                currency=(r.get('Moneda') or None),
                iva=iva[:40] if iva else None,
                unit_per_pack=bulto,
                barcode=(str(r.get('Codigo Barras')).strip()[:60] if r.get('Codigo Barras') else None),
                notes=(r.get('Observaciones') or None),
                source_file=archivo,
            )
            db.add(product)
            db.flush()

            # Priority: CLIP matches > spatial heuristic.
            # If CLIP matches file is provided, CLIP is the source of truth:
            # a product without a CLIP match stays imageless (the heuristic
            # fallback would re-introduce filtered-out tables/text bitmaps).
            k = row_key(sup_name, str(r.get('Codigo')) if r.get('Codigo') else None, name)
            if clip_matches:
                srcs = clip_matches.get(k, [])
            else:
                srcs = images_for_row.get(idx, [])
            if srcs:
                for pos, src in enumerate(srcs):
                    db.add(ProductImage(product_id=product.id, src=src, position=pos))
                with_image_count += 1
                total_images_attached += len(srcs)
            else:
                no_image_count += 1

            inserted += 1
            if inserted % 100 == 0:
                db.commit()
                print(f'  ...{inserted}')

        db.commit()
        print(f'OK: importados {inserted} productos en {len(sup_cache)} proveedores')
        print(f'    con foto: {with_image_count} (total {total_images_attached} imágenes)')
        print(f'    sin foto: {no_image_count}')
    finally:
        db.close()


if __name__ == '__main__':
    main()
