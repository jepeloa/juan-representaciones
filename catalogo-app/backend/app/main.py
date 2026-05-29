from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.auth.security import hash_password
from app.routers import (
    auth, products, suppliers, categories,
    admin_users, admin_products, admin_conditions,
    orders,
)


def ensure_initial_admin():
    from decimal import Decimal
    from app.models import PaymentCondition, Setting

    db = SessionLocal()
    try:
        existing = db.execute(
            select(User).where(User.username == settings.INITIAL_ADMIN_USER)
        ).scalar_one_or_none()
        if not existing:
            user = User(
                username=settings.INITIAL_ADMIN_USER,
                password_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
                full_name='Juan',
                is_active=True,
                is_admin=True,
            )
            db.add(user)
            db.commit()
            print(f'Created initial admin user: {settings.INITIAL_ADMIN_USER}')

        # Seed a demo client user so the cliente flow can be tested out of the box
        demo_cliente = db.execute(
            select(User).where(User.username == 'cliente')
        ).scalar_one_or_none()
        if not demo_cliente:
            db.add(User(
                username='cliente',
                password_hash=hash_password('cliente2026'),
                full_name='Cliente Demo',
                is_active=True,
                is_admin=False,
            ))
            db.commit()
            print('Created demo client user: cliente / cliente2026')

        # Seed default payment conditions (only if table is empty)
        has_any = db.execute(select(PaymentCondition).limit(1)).scalar_one_or_none()
        if not has_any:
            defaults = [
                ('Contado',         Decimal('0.9500'),   0, 'Pago al contado, 5% de descuento sobre lista', 1),
                ('Cheque 30 días',  Decimal('1.0000'),  30, 'Precio de lista',                              2),
                ('Cheque 60 días',  Decimal('1.0800'),  60, 'Lista + 8%',                                   3),
                ('Cheque 90 días',  Decimal('1.1500'),  90, 'Lista + 15%',                                  4),
            ]
            for name, mult, days, desc, order_ in defaults:
                db.add(PaymentCondition(name=name, description=desc, multiplier=mult,
                                        days=days, is_active=True, sort_order=order_))
            db.commit()
            print('Seeded default payment conditions')

        # Seed default settings if missing
        defaults_settings = {
            'company_name': 'Catálogo Juan',
            'company_contact': '',
            'catalog_disclaimer': (
                'Los precios del catálogo son estimativos. Esta orden constituye un presupuesto sujeto '
                'a confirmación final del proveedor. Stock y precio pueden variar al momento del cierre.'
            ),
            'catalog_terms': '',
        }
        for key, default_value in defaults_settings.items():
            if not db.get(Setting, key):
                db.add(Setting(key=key, value=default_value))
        db.commit()
    finally:
        db.close()


app = FastAPI(title='Catálogo Consolidado', version='1.0.0')

origins = [o.strip() for o in settings.CORS_ORIGINS.split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(suppliers.router)
app.include_router(categories.router)
app.include_router(orders.router)
app.include_router(admin_users.router)
app.include_router(admin_products.router)
app.include_router(admin_conditions.router)


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.on_event('startup')
def on_startup():
    try:
        ensure_initial_admin()
    except Exception as e:
        print(f'WARN: could not seed admin user yet: {e}')
