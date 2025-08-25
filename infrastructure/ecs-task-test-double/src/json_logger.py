import json
from datetime import datetime, timezone


class JSONLogger:
    def __init__(self):
        self.task_definition_arn = None
        self.invocation_id = None
        self.mocking_session_id = None

    def set_context(self, task_definition_arn=None, invocation_id=None, mocking_session_id=None):
        if task_definition_arn:
            self.task_definition_arn = task_definition_arn
        if invocation_id:
            self.invocation_id = invocation_id
        if mocking_session_id:
            self.mocking_session_id = mocking_session_id

    def log(self, level, message, **kwargs):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "service": "ecs-task-runner"
        }

        if self.task_definition_arn:
            log_entry["taskDefinitionArn"] = self.task_definition_arn
        if self.invocation_id:
            log_entry["invocationId"] = self.invocation_id
        if self.mocking_session_id:
            log_entry["mockingSessionId"] = self.mocking_session_id

        log_entry.update(kwargs)

        print(json.dumps(log_entry, default=str))

    def info(self, message, **kwargs):
        self.log("INFO", message, **kwargs)

    def error(self, message, **kwargs):
        self.log("ERROR", message, **kwargs)

    def debug(self, message, **kwargs):
        self.log("DEBUG", message, **kwargs)
