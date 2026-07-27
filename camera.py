#!/usr/bin/env python3

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PTZPosition:
    pan: float | None = None
    tilt: float | None = None
    zoom: float | None = None


@dataclass
class CameraState:
    position: PTZPosition | None = None
    moving: bool = False


class Camera(ABC):
    """
    Abstract camera interface.

    All camera implementations must provide these methods.
    """

    def __init__(self, name):
        self.name = name


    @abstractmethod
    def connect(self):
        """
        Establish connection to the camera.
        """
        pass


    @abstractmethod
    def disconnect(self):
        """
        Close connection to the camera.
        """
        pass


    @abstractmethod
    def move(
        self,
        pan: float = 0,
        tilt: float = 0,
        zoom: float = 0
    ):
        """
        Relative movement.

        Positive/negative direction depends on the implementation.
        """
        pass


    @abstractmethod
    def stop(self):
        """
        Stop any active movement.
        """
        pass


    @abstractmethod
    def home(self):
        """
        Move to home position.
        """
        pass


    @abstractmethod
    def goto_preset(self, preset):
        """
        Move to a stored preset.
        """
        pass


    @abstractmethod
    def set_preset(self, preset, name):
        """
        Store current position as preset.
        """
        pass


    @abstractmethod
    def get_state(self) -> CameraState:
        """
        Return current camera state.
        """
        pass
