from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.auth.security import hash_password
from app.database import get_db
from app.models import User
from app.schemas import UserCreateIn, UserUpdateIn, UserAdminOut

router = APIRouter(prefix='/api/admin/users', tags=['admin-users'])


@router.get('', response_model=list[UserAdminOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return list(db.execute(select(User).order_by(User.username)).scalars().all())


@router.post('', response_model=UserAdminOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    existing = db.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, f'Ya existe el usuario "{body.username}"')
    user = User(
        username=body.username.strip(),
        password_hash=hash_password(body.password),
        full_name=(body.full_name or None),
        is_admin=body.is_admin,
        is_active=body.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch('/{user_id}', response_model=UserAdminOut)
def update_user(
    user_id: int,
    body: UserUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Usuario no encontrado')
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.is_active is not None:
        # safeguard: do not let an admin deactivate themselves
        if user.id == admin.id and not body.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'No podés desactivar tu propio usuario')
        user.is_active = body.is_active
    if body.password:
        user.password_hash = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return user


@router.delete('/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Usuario no encontrado')
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'No podés eliminar tu propio usuario')
    db.delete(user)
    db.commit()
