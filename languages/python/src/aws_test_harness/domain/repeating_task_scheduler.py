from abc import ABCMeta, abstractmethod


class RepeatingTaskScheduler(metaclass=ABCMeta):
    @abstractmethod
    def schedule(self, task):
        pass

    @abstractmethod
    def scheduled(self) -> bool:
        pass

    @abstractmethod
    def reset_schedule(self):
        pass
