from app.routers import (
    auth, products, suppliers, categories,
    admin_users, admin_products, admin_conditions, admin_payment_terms,
    orders,
)

__all__ = [
    'auth', 'products', 'suppliers', 'categories',
    'admin_users', 'admin_products', 'admin_conditions', 'admin_payment_terms',
    'orders',
]
