from app.repositories.rule_repository import rule_repository
from app.repositories.room_repository import room_repository


class RuleService:
    VALID_METRICS = {"temperature", "humidity", "co2", "motion_detected"}
    VALID_OPERATORS = {">", "<", ">=", "<=", "=="}
    VALID_ACTIONS = {"ON", "OFF", "OPEN", "CLOSE"}

    def _validate(self, payload):
        if payload.metric not in self.VALID_METRICS:
            raise ValueError("metric must be one of temperature, humidity, co2, motion_detected")
        if payload.operator not in self.VALID_OPERATORS:
            raise ValueError("operator is invalid")
        if payload.action not in self.VALID_ACTIONS:
            raise ValueError("action is invalid")

    async def create(self, db, payload):
        self._validate(payload)
        created = await rule_repository.create(db, **payload.model_dump())
        if created.is_active:
            room = await room_repository.get_by_id(db, created.room_id)
            if room and not room.auto_control_enabled:
                await room_repository.update(db, room, {"auto_control_enabled": True})
        return created

    async def list_by_room(self, db, room_id: int):
        return await rule_repository.get_by_room(db, room_id)

    async def update(self, db, rule_id: int, payload):
        rule = await rule_repository.get_by_id(db, rule_id)
        if not rule:
            raise ValueError("Rule not found")
        updates = payload.model_dump(exclude_unset=True)
        metric = updates.get("metric", rule.metric)
        operator = updates.get("operator", rule.operator)
        action = updates.get("action", rule.action)
        if metric not in self.VALID_METRICS or operator not in self.VALID_OPERATORS or action not in self.VALID_ACTIONS:
            raise ValueError("Updated rule is invalid")
        updated_rule = await rule_repository.update(db, rule, updates)
        room = await room_repository.get_by_id(db, updated_rule.room_id)
        if room:
            has_active_rules = await rule_repository.has_active_rules_by_room(db, updated_rule.room_id)
            if room.auto_control_enabled != has_active_rules:
                await room_repository.update(db, room, {"auto_control_enabled": has_active_rules})
        return updated_rule

    async def delete(self, db, rule_id: int):
        rule = await rule_repository.get_by_id(db, rule_id)
        if not rule:
            raise ValueError("Rule not found")
        room_id = rule.room_id
        await rule_repository.delete(db, rule)
        room = await room_repository.get_by_id(db, room_id)
        if room:
            has_active_rules = await rule_repository.has_active_rules_by_room(db, room_id)
            if room.auto_control_enabled != has_active_rules:
                await room_repository.update(db, room, {"auto_control_enabled": has_active_rules})


rule_service = RuleService()
