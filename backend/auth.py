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


async def ensure_can_write_system(current_user: dict = Depends(get_current_user)):
    """Block managers from modifying 'Системные' sections.
    Superadmin: always allowed.
    Administrator: allowed (per-module access enforced by ensure_module_access).
    Manager: forbidden.
    """
    role = current_user.get("role")
    if role not in (UserRole.SUPERADMIN, UserRole.ADMINISTRATOR):
        raise HTTPException(
            status_code=403,
            detail="Раздел «Системные» доступен только администратору ресторана и суперадмину.",
        )
    return current_user


# Whitelist of system-section modules that can be toggled per-restaurant
SYSTEM_MODULES = {
    "caffesta",
    "caffesta_mapping",
    "telegram_bot",
    "cost_control",
    "factual_margin",
}


async def ensure_module_access(restaurant_id: str, module: str, user: dict, write: bool = False) -> None:
    """Verify that:
      - module is enabled for this restaurant (feature flag),
      - user has access to the restaurant,
      - user role is allowed to use the module.

    Superadmin: bypass all checks (regardless of feature flag).
    Administrator: must have restaurant access AND module must be enabled.
    Manager: forbidden for system modules.

    Raises 403/404 with a clear Russian message.
    """
    role = user.get("role")
    if role == UserRole.SUPERADMIN:
        return
    if write and role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Менеджер не имеет доступа к разделу «Системные»")
    if role not in (UserRole.SUPERADMIN, UserRole.ADMINISTRATOR):
        raise HTTPException(status_code=403, detail="Раздел доступен только администратору")
    if restaurant_id not in user.get("restaurant_ids", []):
        raise HTTPException(status_code=403, detail="Нет доступа к этому ресторану")
    rest = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0, "enabled_modules": 1})
    if not rest:
        raise HTTPException(status_code=404, detail="Ресторан не найден")
    enabled = rest.get("enabled_modules") or []
    if module not in enabled:
        raise HTTPException(
            status_code=403,
            detail=f"Модуль «{module}» не подключён для этого ресторана. Обратитесь к суперадмину.",
        )

async def check_restaurant_access(user: dict, restaurant_id: str):
    if user.get("role") == UserRole.SUPERADMIN:
        return True
    if restaurant_id in user.get("restaurant_ids", []):
        return True
    raise HTTPException(status_code=403, detail="Нет доступа к этому ресторану")