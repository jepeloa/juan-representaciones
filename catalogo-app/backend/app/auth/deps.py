from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.database import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/login', auto_error=True)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    if not payload or 'sub' not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Token inválido o expirado')
    user = db.get(User, int(payload['sub']))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Usuario inexistente o deshabilitado')
    return user


def require_admin(current: User = Depends(get_current_user)) -> User:
    if not current.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Se requieren permisos de administrador')
    return current
