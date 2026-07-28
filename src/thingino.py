#!/usr/bin/env python3
# thingino.py
"""
Thingino ONVIF PTZ camera implementation.

This module provides the Camera interface implementation for
Thingino-based cameras using the ONVIF protocol.

Supported features:
- PTZ movement (pan/tilt/zoom)
- Current position reporting
- Movement status reporting
- Preset management
- Home position control

The implementation is used by the MQTT PTZ bridge and exposes
camera state to Home Assistant through MQTT.
"""

import logging
from onvif import ONVIFCamera
from camera import Camera, CameraState, PTZPosition

log = logging.getLogger(__name__)

class ThinginoCamera(Camera):
    """
    ONVIF PTZ camera implementation for Thingino-based cameras.

    Communication is done through the ONVIF PTZ interface.
    """

    def __init__(
        self,
        name,
        host,
        port=80,
        username=None,
        password=None,
        manufacturer="Thingino",
        model="Unknown",
        device_id=None,
        mac=None,
    ):
        super().__init__(
            name=name,
            manufacturer=manufacturer,
            model=model,
            device_id=device_id,
        )

        self.host = host
        self.port = port
        self.username = username
        self.password = password

        self.log = logging.getLogger(
            f"camera.{name}"
        )

        self.cam = None
        self.ptz = None
        self.media = None
        self.profile_token = None
        self.mac = None

        self.presets = {}

    def connect(self):
        """
        Connect to the camera and initialize ONVIF services.
        """

        self.log.info(
            "Connecting to Thingino camera %s (%s)",
            self.name,
            self.host,
        )

        self.cam = ONVIFCamera(
            self.host,
            self.port,
            self.username,
            self.password,
        )

        self.devicemgmt = self.cam.create_devicemgmt_service()
        
        interfaces = self.devicemgmt.GetNetworkInterfaces()
        
        self.log.debug("Interfaces: %s", interfaces)
        
        for interface in interfaces:
            if interface.Info.HwAddress:
                self.mac = interface.Info.HwAddress.lower()
                break
        
        self.ptz = self.cam.create_ptz_service()
        self.media = self.cam.create_media_service()

        profiles = self.media.GetProfiles()

        if not profiles:
            raise RuntimeError(
                "No ONVIF media profiles found"
            )

        # The first ONVIF profile contains the PTZ control token.
        self.profile_token = profiles[0].token

        self.log.info(
            "Connected to %s, profile=%s",
            self.name,
            self.profile_token,
        )

        #self.get_presets()
        
        self.discovery.publish_select(
            camera,
            self.presets[camera.name],
        )


    def disconnect(self):
        """
        Release ONVIF resources.
        """

        self.log.info(
            "Disconnecting %s",
            self.name,
        )

        self.cam = None
        self.ptz = None
        self.media = None
        self.profile_token = None


    def _ensure_connected(self):
        """
        Establish connection when the camera is accessed for the first time.
        """

        if not self.ptz:
            self.connect()


    def get_state(self) -> CameraState:
        """
        Return current PTZ position and movement state.
        """

        self._ensure_connected()

        status = self.ptz.GetStatus(
            {
                "ProfileToken": self.profile_token
            }
        )

        position = None

        if getattr(status, "Position", None):

            zoom = None

            if getattr(status.Position, "Zoom", None):
                zoom = status.Position.Zoom.x

            position = PTZPosition(
                pan=status.Position.PanTilt.x,
                tilt=status.Position.PanTilt.y,
                zoom=zoom,
            )

        moving = False

        move_status = getattr(
            status,
            "MoveStatus",
            None,
        )

        if move_status:
            moving = (
                str(move_status.PanTilt)
                != "IDLE"
            )
            
        self.log.debug(
            "Camera state: pan=%s tilt=%s zoom=%s moving=%s",
            position.pan if position else None,
            position.tilt if position else None,
            position.zoom if position else None,
            moving,
        )

        return CameraState(
            position=position,
            moving=moving,
        )


    def move(
        self,
        pan=0,
        tilt=0,
        zoom=0,
    ):
        """
        Move camera relative to the current position.

        Thingino cameras report movement direction differently
        than expected, therefore the tilt axis is corrected here.
        """

        self._ensure_connected()

        current = self.get_state()

        if not current.position:
            raise RuntimeError(
                "Camera position unavailable"
            )

        current_pan = current.position.pan
        current_tilt = current.position.tilt

        # Thingino tilt direction is inverted compared to ONVIF standard.
        target_pan = pan - current_pan
        target_tilt = current_tilt - tilt

        self.log.debug(
            "Move request pan=%s tilt=%s "
            "current=(%s,%s) delta=(%s,%s)",
            pan,
            tilt,
            current_pan,
            current_tilt,
            target_pan,
            target_tilt,
        )

        request = self.ptz.create_type(
            "RelativeMove"
        )

        request.ProfileToken = self.profile_token

        request.Translation = {
            "PanTilt": {
                "x": target_pan,
                "y": target_tilt,
            }
        }

        self.ptz.RelativeMove(request)


    def stop(self):
        """
        Stop all PTZ movement.
        """

        self._ensure_connected()

        request = self.ptz.create_type(
            "Stop"
        )

        request.ProfileToken = self.profile_token
        request.PanTilt = True
        request.Zoom = True

        self.ptz.Stop(request)

        self.log.debug(
            "Stopping PTZ movement"
        )


    def home(self):
        """
        Move camera to the default home position.
        """

        self._ensure_connected()

        request = self.ptz.create_type(
            "AbsoluteMove"
        )

        request.ProfileToken = self.profile_token

        request.Position = {
            "PanTilt": {
                "x": 0,
                "y": 0,
            }
        }

        self.ptz.AbsoluteMove(request)
        
        self.log.debug(
            "Moving camera to home position"
        )


    def get_presets(self):
        """
        Return available ONVIF presets.
    
        Returns:
            Dictionary mapping preset names to preset tokens.
        """
        if preset not in self.presets:
            self.get_presets()
        
        if preset not in self.presets:
            raise ValueError(
                f"Unknown preset: {preset}"
            )
    
        self._ensure_connected()
    
        request = self.ptz.create_type(
            "GetPresets"
        )
    
        request.ProfileToken = self.profile_token
    
        presets = self.ptz.GetPresets(request)
    
        return {
            preset.Name: preset.token
            for preset in presets
        }

    def set_preset(self, name):
    
        self._ensure_connected()
    
        existing = self.get_presets()
    
        if name in existing:
            self.log.warning(
                "Preset '%s' already exists (token=%s)",
                name,
                existing[name],
            )
    
            return existing[name]
    
    
        request = self.ptz.create_type(
            "SetPreset"
        )
    
        request.ProfileToken = self.profile_token
        request.PresetName = name
    
        token = self.ptz.SetPreset(request)
    
        self.log.info(
            "Created preset '%s' token=%s",
            name,
            token,
        )
    
        return token

    def get_presets(self):
    
        self._ensure_connected()
    
        request = self.ptz.create_type(
            "GetPresets"
        )
    
        request.ProfileToken = self.profile_token
    
        presets = self.ptz.GetPresets(request)
    
        self.presets = {
            preset.Name: preset.token
            for preset in presets
        }
    
        return self.presets
