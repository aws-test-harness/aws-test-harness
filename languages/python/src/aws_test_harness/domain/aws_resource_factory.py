from abc import ABCMeta, abstractmethod


class AwsResourceFactory(metaclass=ABCMeta):
    @abstractmethod
    def get_s3_bucket(self, resource_id):
        pass
