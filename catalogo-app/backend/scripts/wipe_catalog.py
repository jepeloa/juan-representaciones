"""Wipe all catalog data (products + supplier + categories + orders) but keep
users, payment_conditions, settings.

Run with: docker compose exec backend python -m scripts.wipe_catalog
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import Product, ProductImage, Category, Supplier, Order, OrderItem


def main():
    db = SessionLocal()
    try:
        n_oi = db.query(OrderItem).delete()
        n_or = db.query(Order).delete()
        n_pi = db.query(ProductImage).delete()
        n_pr = db.query(Product).delete()
        n_ca = db.query(Category).delete()
        n_su = db.query(Supplier).delete()
        db.commit()
        print(f'Deleted:')
        print(f'  order_items     : {n_oi}')
        print(f'  orders          : {n_or}')
        print(f'  product_images  : {n_pi}')
        print(f'  products        : {n_pr}')
        print(f'  categories      : {n_ca}')
        print(f'  suppliers       : {n_su}')
        print(f'Kept: users, payment_conditions, settings.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
