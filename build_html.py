#!/usr/bin/env python3
"""Generate a self-contained catalogo.html from Catalogo_Consolidado.xlsx.

Reads the consolidated Excel + images/manifest.json and writes a single HTML page
with all data embedded as JS. Images live in the adjacent images/ folder.
"""
from __future__ import annotations
import html
import json
from pathlib import Path

import openpyxl

ROOT = Path('/home/javier/juan')
XLSX = ROOT / 'Catalogo_Consolidado.xlsx'
MANIFEST = ROOT / 'images' / 'manifest.json'
OUT = ROOT / 'catalogo.html'

COLUMNS = [
    'Proveedor', 'Categoria', 'Codigo', 'Producto', 'Descripcion',
    'Precio', 'Moneda', 'IVA', 'Cantidad x Bulto', 'Codigo Barras',
    'Observaciones', 'Archivo origen',
]


def load_rows():
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    ws = wb['Consolidado']
    headers = None
    rows = []
    for r in ws.iter_rows(values_only=True):
        if headers is None:
            headers = [str(v or '').strip() for v in r]
            continue
        if not any(r):
            continue
        rec = {h: v for h, v in zip(headers, r)}
        rows.append(rec)
    wb.close()
    return rows


def load_manifest():
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def normalize(rows, manifest):
    # Assign image src to each row using per-archivo index counter.
    counters: dict[str, int] = {}
    out = []
    suppliers = set()
    categories = set()
    for r in rows:
        proveedor = (r.get('Proveedor') or '').strip()
        archivo = (r.get('Archivo origen') or '').strip()
        cat = (r.get('Categoria') or '').strip()
        if proveedor:
            suppliers.add(proveedor)
        if cat:
            categories.add(cat)
        i = counters.get(archivo, 0)
        counters[archivo] = i + 1
        img_src = None
        if archivo in manifest and manifest[archivo]:
            imgs = manifest[archivo]
            if i < len(imgs):
                img_src = imgs[i].get('src')
            else:
                img_src = imgs[i % len(imgs)].get('src')
        precio = r.get('Precio')
        try:
            precio = float(precio) if precio not in (None, '') else None
        except (TypeError, ValueError):
            precio = None
        out.append({
            'prov': proveedor,
            'cat': cat,
            'cod': (r.get('Codigo') or '') or None,
            'nom': (r.get('Producto') or '') or '',
            'desc': (r.get('Descripcion') or '') or None,
            'precio': precio,
            'mon': (r.get('Moneda') or '') or None,
            'iva': r.get('IVA'),
            'bulto': r.get('Cantidad x Bulto'),
            'barras': r.get('Codigo Barras'),
            'obs': r.get('Observaciones'),
            'archivo': archivo,
            'img': img_src,
        })
    return out, sorted(suppliers), sorted(categories)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Catálogo Consolidado · {date}</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; background: #f4f5f7; color: #1a1a2e; line-height: 1.4; }}
header {{ background: linear-gradient(135deg,#1a1a2e,#2d3a5f); color: #fff; padding: 18px 24px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }}
header h1 {{ font-size: 1.35rem; font-weight: 700; }}
header .meta {{ margin-left: auto; font-size: .82rem; opacity: .8; }}
header .badge {{ background: #4f8ef7; color: #fff; padding: 3px 12px; border-radius: 20px; font-size: .82rem; font-weight: 600; }}

.toolbar {{ background: #fff; border-bottom: 1px solid #dde3ec; padding: 12px 24px; display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; position: sticky; top: 0; z-index: 20; box-shadow: 0 2px 10px rgba(0,0,0,.06); }}
.tg {{ display: flex; flex-direction: column; gap: 3px; min-width: 150px; flex: 1 1 150px; }}
.tg label {{ font-size: .68rem; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: .04em; }}
.tg select, .tg input {{ border: 1px solid #d1d5db; border-radius: 7px; padding: 7px 10px; font-size: .87rem; background: #fff; color: #1a1a2e; outline: none; transition: border-color .12s; }}
.tg select:focus, .tg input:focus {{ border-color: #4f8ef7; }}
.tg input[type=range] {{ padding: 0; cursor: pointer; accent-color: #4f8ef7; }}
.price-display {{ font-size: .78rem; color: #6b7280; }}

.viewtoggle, .btn {{ display: inline-flex; gap: 4px; }}
.viewtoggle button, .btn-reset {{ background: #fff; color: #444; border: 1px solid #d1d5db; padding: 7px 12px; font-size: .82rem; cursor: pointer; transition: background .12s; }}
.viewtoggle button:first-child {{ border-radius: 7px 0 0 7px; }}
.viewtoggle button:last-child {{ border-radius: 0 7px 7px 0; border-left: 0; }}
.viewtoggle button.active {{ background: #4f8ef7; color: #fff; border-color: #4f8ef7; }}
.btn-reset {{ border-radius: 7px; }}
.btn-reset:hover {{ background: #f3f4f6; }}

.stats {{ padding: 8px 24px; font-size: .82rem; color: #6b7280; background: #fafbfc; border-bottom: 1px solid #e5e7eb; }}

/* TABLE VIEW */
.table-wrap {{ overflow-x: auto; padding: 18px 24px; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,.06); font-size: .85rem; }}
thead tr {{ background: #1a1a2e; color: #fff; }}
th {{ padding: 11px 12px; text-align: left; font-weight: 600; white-space: nowrap; cursor: pointer; user-select: none; }}
th:hover {{ background: #2d3a5f; }}
th.asc::after {{ content: ' ▲'; font-size: .7rem; opacity: .75; }}
th.desc::after {{ content: ' ▼'; font-size: .7rem; opacity: .75; }}
th:not(.asc):not(.desc)::after {{ content: ' ⇅'; font-size: .7rem; opacity: .45; }}
tbody tr {{ border-bottom: 1px solid #f0f1f4; transition: background .1s; }}
tbody tr:hover {{ background: #f5f8ff; }}
td {{ padding: 8px 12px; vertical-align: top; max-width: 280px; }}
td.precio {{ text-align: right; font-weight: 700; white-space: nowrap; font-variant-numeric: tabular-nums; }}
td.precio.ars {{ color: #166534; }}
td.precio.usd {{ color: #1e40af; }}
td.thumb {{ width: 56px; padding: 4px; }}
td.thumb img {{ width: 50px; height: 50px; object-fit: cover; border-radius: 4px; cursor: zoom-in; background: #f3f4f6; }}
.badge-prov {{ display: inline-block; padding: 2px 9px; border-radius: 12px; font-size: .73rem; font-weight: 600; white-space: nowrap; background: #e0e7ff; color: #3730a3; }}
.badge-mon {{ display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: .72rem; font-weight: 700; }}
.ars {{ background: #dcfce7; color: #166534; }}
.usd {{ background: #dbeafe; color: #1e40af; }}
.no-price {{ background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-size: .72rem; font-weight: 600; }}

/* GRID VIEW */
.grid {{ padding: 18px 24px; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }}
.card {{ background: #fff; border-radius: 10px; box-shadow: 0 1px 6px rgba(0,0,0,.07); overflow: hidden; display: flex; flex-direction: column; transition: transform .15s, box-shadow .15s; }}
.card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,.1); }}
.card .img-box {{ aspect-ratio: 1; background: #f3f4f6; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
.card .img-box img {{ width: 100%; height: 100%; object-fit: cover; cursor: zoom-in; }}
.card .img-box .placeholder {{ color: #9ca3af; font-size: 2.5rem; }}
.card .info {{ padding: 11px 13px; display: flex; flex-direction: column; gap: 5px; flex: 1; }}
.card .info h3 {{ font-size: .9rem; font-weight: 600; color: #1a1a2e; line-height: 1.3; min-height: 2.4em; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
.card .info .cat {{ font-size: .68rem; color: #6b7280; text-transform: uppercase; letter-spacing: .04em; }}
.card .info .cod {{ font-size: .72rem; color: #4b5563; font-family: ui-monospace, monospace; }}
.card .info .price {{ font-size: 1.05rem; font-weight: 700; margin-top: auto; padding-top: 6px; }}
.card .info .price.ars {{ color: #166534; }}
.card .info .price.usd {{ color: #1e40af; }}

.pager {{ display: flex; align-items: center; justify-content: center; gap: 8px; padding: 18px 24px; }}
.pager button {{ border: 1px solid #d1d5db; background: #fff; color: #444; padding: 6px 14px; border-radius: 7px; cursor: pointer; font-size: .85rem; }}
.pager button:disabled {{ opacity: .35; cursor: default; }}
.pager button:hover:not(:disabled) {{ background: #f3f4f6; }}
.pager span {{ font-size: .85rem; color: #6b7280; min-width: 130px; text-align: center; }}
.no-results {{ text-align: center; padding: 64px 20px; color: #9ca3af; font-size: 1rem; }}

/* MODAL */
.modal {{ position: fixed; inset: 0; background: rgba(0,0,0,.8); display: none; align-items: center; justify-content: center; z-index: 100; padding: 24px; }}
.modal.open {{ display: flex; }}
.modal img {{ max-width: 92vw; max-height: 88vh; border-radius: 6px; }}

/* DETAILS DRAWER */
.details {{ position: fixed; right: 0; top: 0; bottom: 0; width: 380px; background: #fff; box-shadow: -4px 0 18px rgba(0,0,0,.18); transform: translateX(100%); transition: transform .22s; padding: 24px; overflow-y: auto; z-index: 90; }}
.details.open {{ transform: translateX(0); }}
.details .close {{ position: absolute; top: 14px; right: 14px; background: none; border: none; font-size: 1.4rem; cursor: pointer; color: #6b7280; }}
.details img {{ width: 100%; aspect-ratio: 1; object-fit: contain; background: #f9fafb; border-radius: 6px; margin-bottom: 16px; cursor: zoom-in; }}
.details h2 {{ font-size: 1.15rem; margin-bottom: 6px; }}
.details dl {{ display: grid; grid-template-columns: 110px 1fr; gap: 6px 12px; margin-top: 14px; font-size: .87rem; }}
.details dt {{ font-weight: 600; color: #6b7280; }}
.details dd {{ word-break: break-word; }}

@media (max-width: 600px) {{
    .toolbar {{ padding: 10px 12px; }}
    .table-wrap, .grid {{ padding: 10px 8px; }}
    .grid {{ grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }}
    td, th {{ padding: 7px 8px; font-size: .8rem; }}
    .details {{ width: 100%; }}
}}
</style>
</head>
<body>

<header>
    <h1>📦 Catálogo Consolidado</h1>
    <span class="badge" id="total-badge">{n_rows} items</span>
    <div class="meta">Generado el {date}</div>
</header>

<div class="toolbar">
    <div class="tg" style="flex: 2 1 240px;">
        <label>Buscar</label>
        <input type="text" id="q" placeholder="Producto, código, descripción…">
    </div>
    <div class="tg">
        <label>Proveedor</label>
        <select id="f-prov">
            <option value="">Todos</option>
            {prov_options}
        </select>
    </div>
    <div class="tg" style="flex: 2 1 220px;">
        <label>Categoría</label>
        <select id="f-cat">
            <option value="">Todas</option>
            {cat_options}
        </select>
    </div>
    <div class="tg">
        <label>Moneda</label>
        <select id="f-mon">
            <option value="">Todas</option>
            <option value="ARS">ARS</option>
            <option value="USD">USD</option>
        </select>
    </div>
    <div class="tg" style="min-width: 170px; flex: 1.4 1 170px;">
        <label>Precio máximo</label>
        <input type="range" id="f-price" min="0" max="100" step="1" value="100">
        <div class="price-display" id="price-label">Sin límite</div>
    </div>
    <div class="tg" style="flex: 0 0 auto; min-width: 0;">
        <label>Vista</label>
        <div class="viewtoggle">
            <button id="view-table" class="active">Tabla</button>
            <button id="view-grid">Grilla</button>
        </div>
    </div>
    <button class="btn-reset" onclick="resetFilters()">↺ Limpiar</button>
</div>

<div class="stats" id="stats-bar">Cargando…</div>

<div id="view-container">
    <div class="table-wrap" id="table-view">
        <table id="main-table">
            <thead>
                <tr>
                    <th data-col="img">Foto</th>
                    <th data-col="prov">Proveedor</th>
                    <th data-col="cat">Categoría</th>
                    <th data-col="cod">Código</th>
                    <th data-col="nom" style="min-width: 200px">Producto</th>
                    <th data-col="desc" style="min-width: 180px">Descripción</th>
                    <th data-col="precio">Precio</th>
                    <th data-col="mon">Mon.</th>
                    <th data-col="iva">IVA</th>
                </tr>
            </thead>
            <tbody id="tbody"></tbody>
        </table>
    </div>
    <div class="grid" id="grid-view" style="display:none"></div>
    <div class="no-results" id="no-results" style="display:none">Sin resultados para los filtros aplicados.</div>
</div>

<div class="pager">
    <button id="btn-prev">← Anterior</button>
    <span id="pager-info"></span>
    <button id="btn-next">Siguiente →</button>
</div>

<div class="modal" id="modal" onclick="closeModal()"><img id="modal-img" src="" alt=""></div>

<div class="details" id="details">
    <button class="close" onclick="closeDetails()">×</button>
    <img id="d-img" src="" alt="" onclick="openModal(this.src)">
    <h2 id="d-name"></h2>
    <span class="badge-prov" id="d-prov"></span>
    <dl id="d-fields"></dl>
</div>

<script>
const DATA = {data_json};
const CATS_BY_PROV = {cats_by_prov_json};
const PROVS = {provs_json};
const PAGE_SIZE = 60;

// Build accent-insensitive search keys upfront.
DATA.forEach(r => {{
    r._search = (
        (r.prov || '') + ' ' + (r.cat || '') + ' ' + (r.cod || '') + ' ' +
        (r.nom || '') + ' ' + (r.desc || '') + ' ' + (r.obs || '')
    ).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}});

const state = {{ q: '', prov: '', cat: '', mon: '', maxPrice: Infinity, page: 0, sort: null, dir: 'asc', view: 'table' }};
const PRICE_LEVELS = [0, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000, 2500000, 5000000, Infinity];

const $ = id => document.getElementById(id);

function fmtPrice(n, mon) {{
    if (n === null || n === undefined) return '';
    const fmt = new Intl.NumberFormat('es-AR', {{ minimumFractionDigits: 0, maximumFractionDigits: 2 }});
    return (mon === 'USD' ? 'US$ ' : '$ ') + fmt.format(n);
}}

function filtered() {{
    return DATA.filter(r => {{
        if (state.prov && r.prov !== state.prov) return false;
        if (state.cat && r.cat !== state.cat) return false;
        if (state.mon && r.mon !== state.mon) return false;
        if (state.maxPrice !== Infinity && (r.precio === null || r.precio === undefined || r.precio > state.maxPrice)) return false;
        if (state.q) {{
            const q = state.q.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
            if (!r._search.includes(q)) return false;
        }}
        return true;
    }});
}}

function sorted(rows) {{
    if (!state.sort) return rows;
    const k = state.sort, dir = state.dir === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {{
        let av = a[k], bv = b[k];
        if (av === null || av === undefined) av = (k === 'precio') ? Infinity : '';
        if (bv === null || bv === undefined) bv = (k === 'precio') ? Infinity : '';
        if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
        return String(av).localeCompare(String(bv), 'es') * dir;
    }});
}}

function render() {{
    const all = sorted(filtered());
    const total = all.length;
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (state.page >= pages) state.page = pages - 1;
    if (state.page < 0) state.page = 0;
    const slice = all.slice(state.page * PAGE_SIZE, (state.page + 1) * PAGE_SIZE);

    $('total-badge').textContent = total + (total === DATA.length ? ' items' : ` / ${{DATA.length}}`);
    $('stats-bar').textContent = total ? `${{total}} resultado${{total !== 1 ? 's' : ''}} · Página ${{state.page + 1}} de ${{pages}}` : 'Sin resultados';
    $('pager-info').textContent = total ? `Página ${{state.page + 1}} / ${{pages}}` : '';
    $('btn-prev').disabled = state.page === 0;
    $('btn-next').disabled = state.page >= pages - 1;
    $('no-results').style.display = total ? 'none' : 'block';

    if (state.view === 'table') {{
        $('table-view').style.display = '';
        $('grid-view').style.display = 'none';
        renderTable(slice);
    }} else {{
        $('table-view').style.display = 'none';
        $('grid-view').style.display = '';
        renderGrid(slice);
    }}

    // Update sort indicators
    document.querySelectorAll('th[data-col]').forEach(th => {{
        th.classList.remove('asc', 'desc');
        if (state.sort === th.dataset.col) th.classList.add(state.dir);
    }});

    syncURL();
}}

function renderTable(rows) {{
    const tb = $('tbody');
    tb.innerHTML = rows.map((r, i) => {{
        const idx = state.page * PAGE_SIZE + i;
        const img = r.img ? `<img loading="lazy" src="${{r.img}}" alt="" onclick="event.stopPropagation(); openModal('${{r.img}}')">` : '';
        const priceClass = r.mon === 'USD' ? 'usd' : 'ars';
        const priceHtml = r.precio !== null && r.precio !== undefined
            ? `<td class="precio ${{priceClass}}">${{fmtPrice(r.precio, r.mon)}}</td>`
            : `<td class="precio"><span class="no-price">Consultar</span></td>`;
        const monBadge = r.mon ? `<span class="badge-mon ${{r.mon === 'USD' ? 'usd' : 'ars'}}">${{r.mon}}</span>` : '';
        return `<tr onclick="openDetails(${{getDataIndex(r)}})">
            <td class="thumb">${{img}}</td>
            <td><span class="badge-prov">${{r.prov || ''}}</span></td>
            <td>${{escHtml(r.cat || '')}}</td>
            <td>${{escHtml(r.cod || '')}}</td>
            <td>${{escHtml(r.nom || '')}}</td>
            <td title="${{escHtml(r.desc || '')}}">${{escHtml((r.desc || '').slice(0, 130))}}${{(r.desc || '').length > 130 ? '…' : ''}}</td>
            ${{priceHtml}}
            <td>${{monBadge}}</td>
            <td>${{escHtml(String(r.iva ?? ''))}}</td>
        </tr>`;
    }}).join('');
}}

function renderGrid(rows) {{
    const g = $('grid-view');
    g.innerHTML = rows.map((r, i) => {{
        const img = r.img
            ? `<img loading="lazy" src="${{r.img}}" alt="" onclick="event.stopPropagation(); openModal('${{r.img}}')">`
            : '<span class="placeholder">📦</span>';
        const priceClass = r.mon === 'USD' ? 'usd' : 'ars';
        const priceHtml = r.precio !== null && r.precio !== undefined
            ? `<div class="price ${{priceClass}}">${{fmtPrice(r.precio, r.mon)}}</div>`
            : `<div class="price"><span class="no-price">Consultar</span></div>`;
        return `<div class="card" onclick="openDetails(${{getDataIndex(r)}})">
            <div class="img-box">${{img}}</div>
            <div class="info">
                <div class="cat">${{escHtml((r.prov || '') + (r.cat ? ' · ' + r.cat : ''))}}</div>
                <h3 title="${{escHtml(r.nom || '')}}">${{escHtml(r.nom || '')}}</h3>
                ${{r.cod ? `<div class="cod">${{escHtml(r.cod)}}</div>` : ''}}
                ${{priceHtml}}
            </div>
        </div>`;
    }}).join('');
}}

const indexMap = new Map(DATA.map((r, i) => [r, i]));
function getDataIndex(r) {{ return indexMap.get(r); }}

function escHtml(s) {{
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
}}

function openDetails(idx) {{
    const r = DATA[idx];
    if (!r) return;
    $('d-name').textContent = r.nom || '';
    $('d-prov').textContent = r.prov || '';
    $('d-img').src = r.img || '';
    $('d-img').style.display = r.img ? '' : 'none';
    const fields = [
        ['Categoría', r.cat],
        ['Código', r.cod],
        ['Descripción', r.desc],
        ['Precio', r.precio !== null && r.precio !== undefined ? fmtPrice(r.precio, r.mon) : 'Consultar'],
        ['Moneda', r.mon],
        ['IVA', r.iva],
        ['Cantidad x Bulto', r.bulto],
        ['Código de barras', r.barras],
        ['Observaciones', r.obs],
        ['Archivo origen', r.archivo],
    ];
    $('d-fields').innerHTML = fields.filter(([_, v]) => v !== null && v !== undefined && v !== '').map(([k, v]) => `<dt>${{k}}</dt><dd>${{escHtml(String(v))}}</dd>`).join('');
    $('details').classList.add('open');
}}

function closeDetails() {{ $('details').classList.remove('open'); }}
function openModal(src) {{ $('modal-img').src = src; $('modal').classList.add('open'); }}
function closeModal() {{ $('modal').classList.remove('open'); }}

function updateCategoryOptions() {{
    const cats = state.prov ? (CATS_BY_PROV[state.prov] || []) : Object.values(CATS_BY_PROV).flat();
    const unique = [...new Set(cats)].sort();
    const sel = $('f-cat');
    const current = sel.value;
    sel.innerHTML = '<option value="">Todas</option>' + unique.map(c => `<option value="${{escHtml(c)}}">${{escHtml(c)}}</option>`).join('');
    if (unique.includes(current)) sel.value = current; else state.cat = '';
}}

function priceFromSlider(v) {{
    const n = parseInt(v, 10);
    if (n >= 100) return Infinity;
    // Map 0..99 to 0..max(prices) on a log-ish scale
    const max = DATA.reduce((m, r) => r.precio && r.precio > m && r.precio < 1e9 ? r.precio : m, 0);
    return max * Math.pow(n / 100, 2.5);
}}

function syncURL() {{
    const params = new URLSearchParams();
    if (state.q) params.set('q', state.q);
    if (state.prov) params.set('prov', state.prov);
    if (state.cat) params.set('cat', state.cat);
    if (state.mon) params.set('mon', state.mon);
    if (state.view !== 'table') params.set('view', state.view);
    if (state.maxPrice !== Infinity) params.set('max', Math.round(state.maxPrice));
    history.replaceState(null, '', '#' + params.toString());
}}

function readURL() {{
    const params = new URLSearchParams(location.hash.replace(/^#/, ''));
    if (params.has('q')) {{ state.q = params.get('q'); $('q').value = state.q; }}
    if (params.has('prov')) {{ state.prov = params.get('prov'); $('f-prov').value = state.prov; }}
    if (params.has('mon')) {{ state.mon = params.get('mon'); $('f-mon').value = state.mon; }}
    if (params.has('view')) {{ state.view = params.get('view'); }}
    if (params.has('max')) {{ state.maxPrice = parseFloat(params.get('max')); }}
    updateCategoryOptions();
    if (params.has('cat')) {{ state.cat = params.get('cat'); $('f-cat').value = state.cat; }}
    if (state.view === 'grid') {{ $('view-table').classList.remove('active'); $('view-grid').classList.add('active'); }}
}}

function resetFilters() {{
    state.q = ''; $('q').value = '';
    state.prov = ''; $('f-prov').value = '';
    state.cat = ''; updateCategoryOptions(); $('f-cat').value = '';
    state.mon = ''; $('f-mon').value = '';
    state.maxPrice = Infinity; $('f-price').value = 100; $('price-label').textContent = 'Sin límite';
    state.page = 0;
    render();
}}

// Event wiring
$('q').addEventListener('input', e => {{ state.q = e.target.value; state.page = 0; render(); }});
$('f-prov').addEventListener('change', e => {{ state.prov = e.target.value; state.cat = ''; updateCategoryOptions(); state.page = 0; render(); }});
$('f-cat').addEventListener('change', e => {{ state.cat = e.target.value; state.page = 0; render(); }});
$('f-mon').addEventListener('change', e => {{ state.mon = e.target.value; state.page = 0; render(); }});
$('f-price').addEventListener('input', e => {{
    state.maxPrice = priceFromSlider(e.target.value);
    $('price-label').textContent = state.maxPrice === Infinity ? 'Sin límite' : 'Hasta ' + fmtPrice(state.maxPrice, 'ARS');
    state.page = 0; render();
}});
$('view-table').addEventListener('click', () => {{ state.view = 'table'; $('view-table').classList.add('active'); $('view-grid').classList.remove('active'); render(); }});
$('view-grid').addEventListener('click', () => {{ state.view = 'grid'; $('view-grid').classList.add('active'); $('view-table').classList.remove('active'); render(); }});
$('btn-prev').addEventListener('click', () => {{ state.page--; render(); window.scrollTo({{ top: 0, behavior: 'smooth' }}); }});
$('btn-next').addEventListener('click', () => {{ state.page++; render(); window.scrollTo({{ top: 0, behavior: 'smooth' }}); }});
document.querySelectorAll('th[data-col]').forEach(th => {{
    th.addEventListener('click', () => {{
        const k = th.dataset.col;
        if (state.sort === k) {{ state.dir = state.dir === 'asc' ? 'desc' : 'asc'; }}
        else {{ state.sort = k; state.dir = 'asc'; }}
        render();
    }});
}});
document.addEventListener('keydown', e => {{
    if (e.key === 'Escape') {{ closeModal(); closeDetails(); }}
}});

updateCategoryOptions();
readURL();
render();
</script>
</body>
</html>
"""


def main():
    rows = load_rows()
    manifest = load_manifest()
    items, suppliers, categories = normalize(rows, manifest)
    # Build per-supplier category map for cascading filter
    cats_by_prov: dict[str, list[str]] = {}
    for r in items:
        if r['cat']:
            cats_by_prov.setdefault(r['prov'], set()).add(r['cat'])
    cats_by_prov = {k: sorted(v) for k, v in cats_by_prov.items()}

    prov_options = ''.join(f'<option value="{html.escape(p)}">{html.escape(p)}</option>' for p in suppliers)
    cat_options = ''.join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in categories)

    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')

    out = HTML_TEMPLATE.format(
        n_rows=len(items),
        date=today,
        data_json=json.dumps(items, ensure_ascii=False, separators=(',', ':')),
        cats_by_prov_json=json.dumps(cats_by_prov, ensure_ascii=False, separators=(',', ':')),
        provs_json=json.dumps(suppliers, ensure_ascii=False, separators=(',', ':')),
        prov_options=prov_options,
        cat_options=cat_options,
    )
    OUT.write_text(out, encoding='utf-8')
    size_kb = OUT.stat().st_size / 1024
    print(f'Wrote {OUT} ({size_kb:.1f} KB, {len(items)} rows)')


if __name__ == '__main__':
    main()
