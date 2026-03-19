from app.domain.condition_evaluator import ConditionEvaluator


class AutomationEngine:
    async def evaluate_rules(self, reading, rules, alert_service, device_service, db):
        executed = []
        for rule in rules:
            current_value = getattr(reading, rule.metric, None)
            if ConditionEvaluator.evaluate(current_value, rule.operator, rule.threshold_value):
                existing_alert = await alert_service.get_open_alert(
                    db=db,
                    room_id=reading.room_id,
                    level=rule.alert_level,
                    message=rule.alert_message,
                )
                if existing_alert:
                    alert = existing_alert
                else:
                    alert = await alert_service.create(
                        db=db,
                        room_id=reading.room_id,
                        level=rule.alert_level,
                        message=rule.alert_message,
                    )
                executed.append({"rule_id": rule.id, "alert_id": alert.id})
                if rule.target_device_id:
                    try:
                        device = await device_service.control(
                            db=db,
                            device_id=rule.target_device_id,
                            action=rule.action,
                            source="RULE",
                            description=f"Triggered by rule {rule.name}",
                        )
                        executed[-1]["device_id"] = device.id
                    except ValueError:
                        pass
        return executed


automation_engine = AutomationEngine()
