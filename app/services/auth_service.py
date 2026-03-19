from sqlalchemy import select
from app.models.user import User
from app.core.security import verify_password, create_access_token, hash_password


class AuthService:
    async def login(self, db, email: str, password: str):
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")
        return create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})

    async def seed_admin_if_empty(self, db):
        result = await db.execute(select(User).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        user = User(
            full_name="System Admin",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def create_user(self, db, full_name: str, email: str, password: str):
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ValueError("Email already exists")
        
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role="user",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def list_users(self, db):
        result = await db.execute(select(User).order_by(User.id.asc()))
        return result.scalars().all()

    async def delete_user(self, db, user_id: int):
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        await db.delete(user)
        await db.commit()
     
auth_service = AuthService()
