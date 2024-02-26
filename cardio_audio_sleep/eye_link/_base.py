from abc import ABC, abstractmethod


class BaseEyelink(ABC):
    """Base class for eye-link device."""

    @abstractmethod
    def __init__(self, pname, fname, host_ip):
        pass

    @abstractmethod
    def calibrate(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def signal(self, value: str):
        pass

    @abstractmethod
    def close(self):
        pass
