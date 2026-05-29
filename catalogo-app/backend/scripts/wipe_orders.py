"""Delete only orders + order_items (keep everything else)."""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import Order, OrderItem


def main():
    db = SessionLocal()
    try:
        n_oi = db.query(OrderItem).delete()
        n_or = db.query(Order).delete()
        db.commit()
        print(f'Deleted: orders={n_or}, order_items={n_oi}')
        print('Kept everything else (users, products, suppliers, etc.)')
    finally:
        db.close()


if __name__ == '__main__':
    main()
