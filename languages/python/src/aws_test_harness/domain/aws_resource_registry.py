from abc import ABCMeta, abstractmethod


class AwsResourceRegistry(metaclass=ABCMeta):
    @abstractmethod
    def get_resource_arn(self, resource_id):
        pass
