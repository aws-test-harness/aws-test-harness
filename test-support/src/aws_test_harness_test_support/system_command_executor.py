import subprocess
from logging import Logger
from typing import Sequence, Optional, Mapping


class SystemCommandExecutor:
    def __init__(self, logger: Logger):
        self.__logger = logger

    def execute(self, command_args: Sequence[str], env_vars: Optional[Mapping[str, str]] = None,
                timeout_seconds: int = 10) -> None:
        self.__logger.info('Executing command: %s', subprocess.list2cmdline(command_args))

        completed_process = subprocess.run(
            command_args,
            capture_output=True, timeout=timeout_seconds, env=env_vars if env_vars else {}, encoding='utf-8'
        )

        if completed_process.stdout:
            self.__logger.info('Process stdout:\n%s', completed_process.stdout)

        if completed_process.stderr:
            self.__logger.info('Process stderr:\n%s', completed_process.stderr)

        completed_process.check_returncode()
