"""End-to-end test of the Catálogo Juan app with Playwright.

Captures screenshots for the user manual at each step.
"""
from __future__ import annotations
import asyncio
import os
import re
from pathlib import Path
from playwright.async_api import async_playwright, Page

BASE = os.environ.get('BASE_URL', 'http://24.199.118.218:8003')
SHOTS = Path(__file__).parent / 'screenshots'
SHOTS.mkdir(exist_ok=True)
REPORT = []


def log(msg: str):
    print(msg, flush=True)
    REPORT.append(msg)


async def shot(page: Page, name: str, full_page: bool = False):
    path = SHOTS / f'{name}.png'
    await page.screenshot(path=str(path), full_page=full_page)
    log(f'  📸 {name}.png')


async def safe_click(page: Page, locator_or_str, timeout: int = 5000):
    try:
        loc = page.locator(locator_or_str) if isinstance(locator_or_str, str) else locator_or_str
        await loc.first.click(timeout=timeout)
        return True
    except Exception as e:
        log(f'    ⚠ safe_click failed for {locator_or_str!r}: {type(e).__name__}')
        return False


async def login(page: Page, username: str, password: str):
    await page.goto(f'{BASE}/login')
    await page.wait_for_load_state('networkidle')
    await page.fill('input[name="username"]', username)
    await page.fill('input[name="password"]', password)
    await page.click('button[type="submit"]')
    await page.wait_for_url('**/catalogo', timeout=10_000)
    await page.wait_for_load_state('networkidle')


async def goto_nav(page: Page, label: str):
    """Navigate via a sidebar nav item by visible label."""
    link = page.locator(f'aside a:has-text("{label}")').first
    await link.click()
    await page.wait_for_load_state('networkidle')


async def logout(page: Page):
    # User menu: first round button in header (avatar)
    await page.locator('header button').filter(has=page.locator('.rounded-full')).first.click()
    await page.wait_for_timeout(300)
    await page.get_by_text('Cerrar sesión').click()
    await page.wait_for_url('**/login', timeout=5000)


# ============== ADMIN FLOW ==============
async def test_admin(p):
    log('\n## ADMIN DESKTOP FLOW')
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(viewport={'width': 1440, 'height': 900})
    page = await ctx.new_page()
    # auto-accept dialogs (delete confirms)
    page.on('dialog', lambda d: asyncio.create_task(d.accept()))

    try:
        # 01 Login page
        await page.goto(f'{BASE}/login')
        await page.wait_for_load_state('networkidle')
        await shot(page, '01_login')

        # 02 Catalogo (table view, admin)
        await page.fill('input[name="username"]', 'juan')
        await page.fill('input[name="password"]', 'juan2026')
        await page.click('button[type="submit"]')
        await page.wait_for_url('**/catalogo', timeout=10_000)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(500)
        await shot(page, '02_admin_catalogo_table')
        log('  ✓ Login admin')

        # 03 Grid view
        await safe_click(page, 'button:has-text("Grilla")')
        await page.wait_for_timeout(600)
        await shot(page, '03_admin_catalogo_grid')

        # back to table
        await safe_click(page, 'button:has-text("Tabla")')
        await page.wait_for_timeout(400)

        # 04 Search
        await page.locator('input[placeholder*="Producto"]').first.fill('fadeco')
        await page.wait_for_timeout(900)
        await shot(page, '04_admin_busqueda_fadeco')
        await page.locator('input[placeholder*="Producto"]').first.fill('')
        await page.wait_for_timeout(900)

        # 05 Product detail modal (click a row)
        await page.locator('tbody tr').first.click()
        await page.wait_for_timeout(800)
        await shot(page, '05_admin_product_detail_modal')
        # close
        await page.keyboard.press('Escape')
        # try clicking the X close
        if await page.locator('button[aria-label="Cerrar"]').count() > 0:
            await page.locator('button[aria-label="Cerrar"]').first.click()
        await page.wait_for_timeout(400)

        # 06 Add to cart from catalog: click +
        first_add = page.locator('tbody tr button[title="Agregar a la orden"]').first
        await first_add.click()
        await page.wait_for_timeout(400)
        # Now the row has a quantity control. Click + on it to add another.
        plus_btn = page.locator('tbody tr div.bg-sage-50 button:has-text("+")').first
        await plus_btn.click()
        await page.wait_for_timeout(300)
        # And another product
        first_add_2 = page.locator('tbody tr button[title="Agregar a la orden"]').first
        await first_add_2.click()
        await page.wait_for_timeout(400)
        await shot(page, '06_admin_inline_quantity')

        # 07 Sidebar shows cart badge — go to /admin/productos
        await goto_nav(page, 'Cargar productos')
        await page.wait_for_timeout(700)
        await shot(page, '07_admin_productos_lista')

        # 08 Open new product form
        await safe_click(page, 'button:has-text("Nuevo producto"), button:has-text("Nuevo")')
        await page.wait_for_timeout(500)
        await shot(page, '08_admin_productos_form_nuevo')

        # 09 Fill form
        # Click "+ Nuevo" next to supplier
        await page.locator('button:has-text("+ Nuevo")').first.click()
        await page.wait_for_timeout(300)
        await page.locator('input[placeholder*="nuevo proveedor"]').fill('Test E2E')
        await page.locator('input[name="name"]').fill('Producto de prueba E2E')
        await page.locator('input[name="code"]').fill('E2E-001')
        await page.locator('textarea[name="description"]').fill('Producto creado por el test automatizado.')
        await page.locator('input[name="price"]').fill('123456.78')
        await shot(page, '09_admin_productos_form_lleno')

        await page.locator('form button[type="submit"]').last.click()
        await page.wait_for_timeout(2000)
        await page.wait_for_load_state('networkidle')
        await shot(page, '10_admin_productos_creado')
        log('  ✓ Producto creado')

        # 11 Edit it
        search = page.locator('input[placeholder*="Producto"]').first
        await search.fill('Producto de prueba E2E')
        await page.wait_for_timeout(1000)
        if await page.locator('button:has-text("Editar")').count():
            await page.locator('button:has-text("Editar")').first.click()
            await page.wait_for_timeout(700)
            await shot(page, '11_admin_productos_editar')

            await page.locator('input[name="price"]').fill('150000')
            await page.locator('form button[type="submit"]').last.click()
            await page.wait_for_timeout(2000)
            await shot(page, '12_admin_productos_actualizado')

            # Delete it
            await search.fill('Producto de prueba E2E')
            await page.wait_for_timeout(1000)
            if await page.locator('button:has-text("Eliminar")').count():
                await page.locator('button:has-text("Eliminar")').first.click()
                await page.wait_for_timeout(1500)
            log('  ✓ Producto eliminado')

        # 13 Condiciones
        await goto_nav(page, 'Condiciones')
        await page.wait_for_timeout(700)
        await shot(page, '13_admin_condiciones')

        # 14 New condition
        await safe_click(page, 'button:has-text("Nueva condición")')
        await page.wait_for_timeout(500)
        if await page.locator('input[name="cname"]').count():
            await page.locator('input[name="cname"]').fill('Test 45 días')
            await page.locator('input[name="cdesc"]').fill('Condición creada por el test')
            await page.locator('input[name="cmult"]').fill('1.05')
            await page.locator('input[name="cdays"]').fill('45')
            await shot(page, '14_admin_condiciones_form')
            await page.locator('button[type="submit"]:has-text("Crear")').click()
            await page.wait_for_timeout(1500)
            # delete the just-created
            await page.locator('button:has-text("Eliminar")').last.click()
            await page.wait_for_timeout(1500)

        # 15 Email notification field
        email_field = page.locator('input[name="notif_email"]')
        if await email_field.count():
            await email_field.fill('ventas-demo@empresa.com')
            await shot(page, '15_admin_condiciones_email')
            await page.locator('button:has-text("Guardar términos")').click()
            await page.wait_for_timeout(1500)
            log('  ✓ Email de notificación guardado')

        # 16 Usuarios
        await goto_nav(page, 'Usuarios')
        await page.wait_for_timeout(700)
        await shot(page, '16_admin_usuarios')

        # 17 New user
        await safe_click(page, 'button:has-text("Nuevo usuario"), button:has-text("Nuevo")')
        await page.wait_for_timeout(500)
        if await page.locator('input[name="username"]').count():
            await page.locator('input[name="username"]').fill('cliente_e2e')
            await page.locator('input[name="full_name"]').fill('Cliente E2E')
            await page.locator('input[name="password"]').fill('e2e2026')
            await shot(page, '17_admin_usuarios_form')

            await page.locator('button[type="submit"]:has-text("Crear")').click()
            await page.wait_for_timeout(1500)
            await shot(page, '18_admin_usuarios_creado')

            # delete the created user
            del_btns = page.locator('button:has-text("Eliminar")')
            if await del_btns.count():
                await del_btns.last.click()
                await page.wait_for_timeout(1500)
            log('  ✓ Usuario creado y eliminado')

        # 19 Suppliers
        await goto_nav(page, 'Proveedores')
        await page.wait_for_timeout(700)
        await shot(page, '19_proveedores')

        # logout
        try:
            await logout(page)
            log('  ✓ Logout admin')
        except Exception as e:
            log(f'  ⚠ logout: {e}')

    finally:
        await ctx.close()
        await browser.close()


# ============== CLIENT FLOW ==============
async def test_client(p):
    log('\n## CLIENT DESKTOP FLOW')
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(viewport={'width': 1440, 'height': 900})
    page = await ctx.new_page()

    try:
        await login(page, 'cliente', 'cliente2026')
        await page.wait_for_timeout(700)
        await shot(page, '20_cliente_catalogo')
        log('  ✓ Login cliente')

        # Add a couple of products
        add_btns = page.locator('tbody tr button[title="Agregar a la orden"]')
        n = await add_btns.count()
        if n > 0:
            await add_btns.first.click()
            await page.wait_for_timeout(400)
            # use the inline + that appeared
            plus = page.locator('tbody tr div.bg-sage-50 button:has-text("+")').first
            await plus.click()
            await page.wait_for_timeout(300)
            # add another product
            await page.locator('tbody tr button[title="Agregar a la orden"]').first.click()
            await page.wait_for_timeout(400)
        await shot(page, '21_cliente_carrito_inline')

        # Go to cart
        await goto_nav(page, 'Mi orden')
        await page.wait_for_timeout(700)
        await shot(page, '22_cliente_carrito')

        # Increase qty
        if await page.locator('button[aria-label="Sumar"]').count():
            await page.locator('button[aria-label="Sumar"]').first.click()
            await page.wait_for_timeout(300)
            await shot(page, '23_cliente_carrito_qty')

        # Pick payment condition (60 días)
        sel = page.locator('select').first
        await sel.select_option(index=2)  # Cheque 60 días
        await page.wait_for_timeout(400)
        await page.locator('textarea').first.fill('Pedido generado desde test automatizado E2E.')
        await shot(page, '24_cliente_carrito_condicion')

        # Generate order
        await page.locator('button:has-text("Crear orden")').click()
        # wait for email background task + status refresh
        await page.wait_for_timeout(4000)
        await shot(page, '25_cliente_orden_creada')
        log('  ✓ Orden creada')

        await logout(page)
    finally:
        await ctx.close()
        await browser.close()


# ============== MOBILE FLOW ==============
async def test_mobile(p):
    log('\n## MOBILE FLOW (iPhone 13 viewport)')
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(
        viewport={'width': 390, 'height': 844},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
    )
    page = await ctx.new_page()

    try:
        await page.goto(f'{BASE}/login')
        await page.wait_for_load_state('networkidle')
        await shot(page, '30_mobile_login')

        await page.fill('input[name="username"]', 'cliente')
        await page.fill('input[name="password"]', 'cliente2026')
        await page.click('button[type="submit"]')
        await page.wait_for_url('**/catalogo', timeout=10_000)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(700)
        await shot(page, '31_mobile_catalogo')

        # Open hamburger menu
        hamburger = page.locator('header button[aria-label="Abrir menú"]').first
        await hamburger.click()
        await page.wait_for_timeout(500)
        await shot(page, '32_mobile_sidebar')
        # close it
        close_btn = page.locator('aside button[aria-label="Cerrar menú"]').first
        await close_btn.click()
        await page.wait_for_timeout(500)

        # Add a product (mobile uses card layout, button has aria-label)
        add_btn = page.locator('button[aria-label="Agregar a la orden"]').first
        await add_btn.click()
        await page.wait_for_timeout(400)
        # add another via inline +
        plus = page.locator('div.bg-sage-50 button:has-text("+")').first
        await plus.click()
        await page.wait_for_timeout(300)
        await shot(page, '33_mobile_catalogo_carrito')

        # Open cart via topbar shortcut icon
        await page.locator('header a[href="/carrito"]').first.click()
        await page.wait_for_url('**/carrito', timeout=5000)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(700)
        await shot(page, '34_mobile_carrito')

        # Submit order
        await page.locator('button:has-text("Crear orden")').click()
        await page.wait_for_timeout(4000)
        await shot(page, '35_mobile_orden_creada')
        log('  ✓ Orden generada en mobile')
    finally:
        await ctx.close()
        await browser.close()


async def main():
    log(f'E2E test against {BASE}')
    log(f'Screenshots → {SHOTS}')
    async with async_playwright() as p:
        try:
            await test_admin(p)
        except Exception as e:
            log(f'✗ admin flow: {e}')
        try:
            await test_client(p)
        except Exception as e:
            log(f'✗ client flow: {e}')
        try:
            await test_mobile(p)
        except Exception as e:
            log(f'✗ mobile flow: {e}')

    log('\n✓ Done')
    Path(__file__).parent.joinpath('e2e_report.txt').write_text('\n'.join(REPORT), encoding='utf-8')


if __name__ == '__main__':
    asyncio.run(main())
