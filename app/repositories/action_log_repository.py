from app.models.action_log import ActionLog
from app.repositories.base import BaseRepository


class ActionLogRepository(BaseRepository):
    def __init__(self):
        super().__init__(ActionLog)


action_log_repository = ActionLogRepository()
