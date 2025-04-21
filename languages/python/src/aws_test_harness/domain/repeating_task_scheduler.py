from abc import ABCMeta, abstractmethod
from typing import Callable, Any


class RepeatingTaskScheduler(metaclass=ABCMeta):
    @abstractmethod
    def schedule(self, task: Callable[..., Any]) -> None:
        pass

    @abstractmethod
    def scheduled(self) -> bool:
        pass

    @abstractmethod
    def reset_schedule(self) -> None:
        pass
