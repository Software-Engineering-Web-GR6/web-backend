from sqlalchemy import select
from app.models.automation_rule import AutomationRule
from app.repositories.base import BaseRepository


class RuleRepository(BaseRepository):
    def __init__(self):
        super().__init__(AutomationRule)

    async def get_active_rules_by_room(self, db, room_id: int):
        result = await db.execute(
            select(AutomationRule).where(
                AutomationRule.room_id == room_id,
                AutomationRule.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get_by_room(self, db, room_id: int):
        result = await db.execute(select(AutomationRule).where(AutomationRule.room_id == room_id))
        return list(result.scalars().all())

    async def set_active_by_room(self, db, room_id: int, is_active: bool):
        rules = await self.get_by_room(db, room_id)
        for rule in rules:
            rule.is_active = is_active
        await db.commit()
        for rule in rules:
            await db.refresh(rule)
        return rules

    async def has_active_rules_by_room(self, db, room_id: int) -> bool:
        rules = await self.get_active_rules_by_room(db, room_id)
        return len(rules) > 0

    async def update(self, db, rule: AutomationRule, updates: dict):
        for key, value in updates.items():
            setattr(rule, key, value)
        await db.commit()
        await db.refresh(rule)
        return rule

    async def delete(self, db, rule: AutomationRule):
        await db.delete(rule)
        await db.commit()


rule_repository = RuleRepository()
