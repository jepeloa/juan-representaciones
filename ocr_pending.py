#!/usr/bin/env python3
"""OCR for image-only PDFs and JPEG files in 'Para revisar'.

Generates text files in 'Listas actualizadas/_txt_ocr/' for downstream parsing.
Uses Tesseract with Spanish language. Renders PDFs at 300 DPI via pdf2image.
"""
from __future__ import annotations
from pathlib import Path
import sys
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

BASE = Path('/home/javier/juan/Listas actualizadas')
OUT = BASE / '_txt_ocr'
OUT.mkdir(exist_ok=True)

# (source_path_relative_to_BASE, output_filename, psm)
TARGETS = [
    ('Don Segura/Don Segura.pdf', 'Don Segura__Don Segura.txt', 6),
    ('Turboblender/LISTA DE PRECIOS DF V.01.26.pdf', 'Turboblender__LISTA DE PRECIOS DF V.01.26.txt', 6),
    ('Turboblender/Lista Turboblender abril 26.pdf', 'Turboblender__Lista Turboblender abril 26.txt', 6),
    ('Havard/PREVENTA CALEFACCION BORGEN 2026 -.pdf', 'Havard__PREVENTA CALEFACCION BORGEN 2026.txt', 6),
    ('Cortadora BIANCHI NOVA  330.pdf', 'Bianchi__Cortadora NOVA 330.txt', 6),
    ('DS Campanas/Nueva linea cristal.jpeg', 'DS Campanas__Nueva linea cristal.txt', 6),
    ('DS Campanas/Piramidal.jpeg', 'DS Campanas__Piramidal.txt', 6),
    ('DS Campanas/semi circular.jpeg', 'DS Campanas__semi circular.txt', 6),
    ('DS Campanas/slim flat.jpeg', 'DS Campanas__slim flat.txt', 6),
    # New for May 2026
    ('Asadores 2026.pdf', 'Asadores_2026.txt', 11),  # psm 11 (sparse text) for catalog with stylized fonts
    ('ARE/Catalogo ARE - Diciembre 2024.pdf', 'ARE__Catalogo.txt', 6),
    ('Dunia/CATALOGO_MAQUINARIA_DUNIA_ABRIL_2026.pdf', 'Dunia__Catalogo maquinaria abril.txt', 6),
]


def ocr_image(img: Image.Image, psm: int) -> str:
    cfg = f'--psm {psm} -l spa'
    return pytesseract.image_to_string(img, config=cfg)


def ocr_pdf(path: Path, psm: int) -> str:
    pages = convert_from_path(str(path), dpi=300)
    parts = []
    for i, page in enumerate(pages, 1):
        parts.append(f'\n===== PAGE {i} =====\n')
        parts.append(ocr_image(page, psm))
    return ''.join(parts)


def ocr_jpeg(path: Path, psm: int) -> str:
    img = Image.open(path)
    return ocr_image(img, psm)


def main():
    only = set(sys.argv[1:])
    for rel, out_name, psm in TARGETS:
        if only and out_name not in only and rel not in only:
            continue
        src = BASE / rel
        out_path = OUT / out_name
        if not src.exists():
            print(f'  MISSING: {src}')
            continue
        print(f'  OCR: {rel} -> {out_name}')
        try:
            if src.suffix.lower() == '.pdf':
                text = ocr_pdf(src, psm)
            else:
                text = ocr_jpeg(src, psm)
            out_path.write_text(text, encoding='utf-8')
            print(f'    {len(text)} chars')
        except Exception as e:
            print(f'    ERROR: {e}')


if __name__ == '__main__':
    main()
