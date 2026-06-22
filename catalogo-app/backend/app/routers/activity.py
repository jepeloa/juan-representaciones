from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import ActivityEvent, User
from app.schemas import ActivityEventIn

router = APIRouter(prefix='/api', tags=['activity'])

# Tipos de evento aceptados desde el front (evita basura en la tabla).
ALLOWED = {
    'page_view', 'product_view', 'add_to_cart',
    'view_conditions', 'view_stock', 'search',
}


def log_event(db: Session, user_id: int | None, event_type: str,
              label: str | None = None, path: str | None = None,
              ref_id: int | None = None) -> None:
    """Helper para registrar actividad desde otros routers (login, órdenes)."""
    ev = ActivityEvent(
        user_id=user_id,
        event_type=event_type,
        label=(label or None),
        path=(path or None),
        ref_id=ref_id,
    )
    db.add(ev)


@router.post('/activity', status_code=status.HTTP_204_NO_CONTENT)
def track_activity(
    body: ActivityEventIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.event_type not in ALLOWED:
        # Ignorar silenciosamente tipos no permitidos (no romper el front).
        return
    ev = ActivityEvent(
        user_id=user.id,
        event_type=body.event_type,
        label=(body.label[:255] if body.label else None),
        path=(body.path[:255] if body.path else None),
        ref_id=body.ref_id,
    )
    db.add(ev)
    db.commit()
