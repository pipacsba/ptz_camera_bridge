#!/usr/bin/env python3
# camera.py
#
# Abstract camera interface used by the MQTT PTZ bridge.
#
# Each camera implementation (Thingino, ONVIF, etc.) must inherit from
# Camera and implement the methods defined below. The bridge interacts
# exclusively with this interface and is therefore independent of the
# underlying camera protocol.

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PTZPosition:
    """
    Current PTZ position reported by the camera.

    Values are implementation-defined. They typically represent the
    normalized pan, tilt and zoom coordinates exposed by the camera.
    """

    pan: float | None = None
    tilt: float | None = None
    zoom: float | None = None


@dataclass
class CameraState:
    """
    Current operational state of the camera.
    """

    position: PTZPosition | None = None
    moving: bool = False


class Camera(ABC):
    """
    Abstract camera interface.

    The MQTT bridge communicates only through this interface, allowing
    different camera implementations to be added without changing the
    bridge itself.
    """

    def __init__(
        self,
        name,
        manufacturer="Unknown",
        model="Unknown",
        device_id=None,
    ):
        self.name = name
        self.manufacturer = manufacturer
        self.model = model
        self.device_id = device_id or f"ptz_{name}"


    @abstractmethod
    def connect(self):
        """
        Establish a connection to the camera.

        Called during bridge startup or after reconnect.
        """
        pass


    @abstractmethod
    def disconnect(self):
        """
        Close the connection to the camera and release resources.
        """
        pass


    @abstractmethod
    def move(
        self,
        pan: float = 0,
        tilt: float = 0,
        zoom: float = 0,
    ):
        """
        Move the camera.

        The interpretation of the supplied coordinates (relative or
        absolute) is implementation-specific.
        """
        pass


    @abstractmethod
    def stop(self):
        """
        Immediately stop any active PTZ movement.
        """
        pass


    @abstractmethod
    def home(self):
        """
        Move the camera to its configured home position.
        """
        pass


    @abstractmethod
    def goto_preset(self, preset):
        """
        Move the camera to a previously stored preset.
        """
        pass


    @abstractmethod
    def set_preset(self, preset, name):
        """
        Store the current camera position as a preset.
        """
        pass


    @abstractmethod
    def get_state(self) -> CameraState:
        """
        Return the current camera state.

        This method should never modify the camera state.
        """
        pass
