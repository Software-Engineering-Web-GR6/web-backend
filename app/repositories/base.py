from sqlalchemy import select


class BaseRepository:
    def __init__(self, model):
        self.model = model

    async def get_by_id(self, db, item_id: int):
        result = await db.execute(select(self.model).where(self.model.id == item_id))
        return result.scalar_one_or_none()

    async def get_all(self, db):
        result = await db.execute(select(self.model))
        return result.scalars().all()

    async def create(self, db, **kwargs):
        item = self.model(**kwargs)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item
