from app.repositories.rule_repository import rule_repository


class RuleService:
    VALID_METRICS = {"temperature", "humidity", "co2"}
    VALID_OPERATORS = {">", "<", ">=", "<=", "=="}
    VALID_ACTIONS = {"ON", "OFF", "OPEN", "CLOSE"}

    def _validate(self, payload):
        if payload.metric not in self.VALID_METRICS:
            raise ValueError("metric must be one of temperature, humidity, co2")
        if payload.operator not in self.VALID_OPERATORS:
            raise ValueError("operator is invalid")
        if payload.action not in self.VALID_ACTIONS:
            raise ValueError("action is invalid")

    async def create(self, db, payload):
        self._validate(payload)
        return await rule_repository.create(db, **payload.model_dump())

    async def list_by_room(self, db, room_id: int):
        return await rule_repository.get_by_room(db, room_id)

    async def update(self, db, rule_id: int, payload):
        rule = await rule_repository.get_by_id(db, rule_id)
        if not rule:
            raise ValueError("Rule not found")
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        metric = updates.get("metric", rule.metric)
        operator = updates.get("operator", rule.operator)
        action = updates.get("action", rule.action)
        if metric not in self.VALID_METRICS or operator not in self.VALID_OPERATORS or action not in self.VALID_ACTIONS:
            raise ValueError("Updated rule is invalid")
        return await rule_repository.update(db, rule, updates)

    async def delete(self, db, rule_id: int):
        rule = await rule_repository.get_by_id(db, rule_id)
        if not rule:
            raise ValueError("Rule not found")
        await rule_repository.delete(db, rule)


rule_service = RuleService()
