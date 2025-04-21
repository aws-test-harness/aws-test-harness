from abc import ABCMeta, abstractmethod


class S3Bucket(metaclass=ABCMeta):
    @abstractmethod
    def put_object(self, **put_object_kwargs) -> None:
        pass
