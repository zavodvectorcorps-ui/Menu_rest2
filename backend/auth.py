from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timezone, timedelta
import os

from database import db
from models import UserRole

SECRET_KEY = os.environ.get('JWT_SECRET')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Неверный токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user

async def require_superadmin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Требуются права суперадмина")
    return current_user

async def check_restaurant_access(user: dict, restaurant_id: str):
    if user.get("role") == UserRole.SUPERADMIN:
        return True
    if restaurant_id in user.get("restaurant_ids", []):
        return True
    raise HTTPException(status_code=403, detail="Нет доступа к этому ресторану")
