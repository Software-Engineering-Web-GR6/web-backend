from sqlalchemy import select

from app.models.user import User
from app.core.security import verify_password, create_access_token, hash_password


class AuthService:
    @staticmethod
    async def login(db, email: str, password: str):
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")

        return create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
            }
        )

    @staticmethod
    async def seed_admin_if_empty(db):
        admin_email = "admin@example.com"

        result = await db.execute(
            select(User).where(User.email == admin_email)
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            return existing_admin

        user = User(
            full_name="System Admin",
            email=admin_email,
            password_hash=hash_password("admin123"),
            role="admin",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


auth_service = AuthService()