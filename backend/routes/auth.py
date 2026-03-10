from fastapi import APIRouter, Depends
from database import db
from models import LoginRequest, UserRole, UserCreate, UserUpdate, User
from auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, require_superadmin
)
from helpers import serialize_doc

router = APIRouter()


@router.post("/auth/login")
async def login(data: LoginRequest):
    user = await db.users.find_one({"username": data.username}, {"_id": 0})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise_auth_error()

    if not user.get("is_active", True):
        raise_auth_error("Пользователь деактивирован")

    access_token = create_access_token(data={"sub": user["id"]})

    if user["role"] == UserRole.SUPERADMIN:
        restaurants = await db.restaurants.find({}, {"_id": 0}).to_list(100)
    else:
        restaurants = await db.restaurants.find({"id": {"$in": user.get("restaurant_ids", [])}}, {"_id": 0}).to_list(100)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "restaurant_ids": user.get("restaurant_ids", [])
        },
        "restaurants": [serialize_doc(r) for r in restaurants]
    }


@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == UserRole.SUPERADMIN:
        restaurants = await db.restaurants.find({}, {"_id": 0}).to_list(100)
    else:
        restaurants = await db.restaurants.find({"id": {"$in": current_user.get("restaurant_ids", [])}}, {"_id": 0}).to_list(100)

    return {
        "user": {
            "id": current_user["id"],
            "username": current_user["username"],
            "role": current_user["role"],
            "restaurant_ids": current_user.get("restaurant_ids", [])
        },
        "restaurants": [serialize_doc(r) for r in restaurants]
    }


# ============ USER MANAGEMENT ============

@router.get("/users")
async def get_users(current_user: dict = Depends(require_superadmin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return [serialize_doc(u) for u in users]


@router.post("/users")
async def create_user(data: UserCreate, current_user: dict = Depends(require_superadmin)):
    from fastapi import HTTPException
    existing = await db.users.find_one({"username": data.username})
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        role=data.role,
        restaurant_ids=data.restaurant_ids
    )
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    doc.pop('password_hash', None)
    return serialize_doc(doc)


@router.put("/users/{user_id}")
async def update_user(user_id: str, data: UserUpdate, current_user: dict = Depends(require_superadmin)):
    from fastapi import HTTPException
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    update_data = {}
    if data.username is not None:
        update_data["username"] = data.username
    if data.password is not None:
        update_data["password_hash"] = get_password_hash(data.password)
    if data.role is not None:
        update_data["role"] = data.role
    if data.restaurant_ids is not None:
        update_data["restaurant_ids"] = data.restaurant_ids
    if data.is_active is not None:
        update_data["is_active"] = data.is_active

    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})

    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return serialize_doc(updated)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_superadmin)):
    from fastapi import HTTPException
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"message": "Пользователь удален"}


def raise_auth_error(detail: str = "Неверный логин или пароль"):
    from fastapi import HTTPException
    raise HTTPException(status_code=401, detail=detail)
