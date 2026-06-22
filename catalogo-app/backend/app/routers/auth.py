from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.auth.security import verify_password, create_access_token
from app.auth.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import LoginIn, TokenOut, UserOut

router = APIRouter(prefix='/api/auth', tags=['auth'])


@router.post('/login', response_model=TokenOut)
def login(creds: LoginIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == creds.username)).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(creds.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Usuario o contraseña incorrectos')
    token = create_access_token(user.id, extra={'username': user.username})
    # Registrar el inicio de sesión como actividad (solo clientes; el admin también queda).
    from app.routers.activity import log_event
    log_event(db, user.id, 'login')
    db.commit()
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get('/me', response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current
