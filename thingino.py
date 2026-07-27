#!/usr/bin/env python3
# thingino.py

import logging

from onvif import ONVIFCamera

from camera import Camera, CameraState, PTZPosition


class ThinginoCamera(Camera):

    def __init__(
        self,
        name,
        host,
        port=80,
        username=None,
        password=None,
    ):
        super().__init__(name)

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


    def connect(self):

        self.log.info(
            "Connecting to Thingino camera %s (%s)",
            self.name,
            self.host
        )

        self.cam = ONVIFCamera(
            self.host,
            self.port,
            self.username,
            self.password,
        )

        self.ptz = self.cam.create_ptz_service()
        self.media = self.cam.create_media_service()

        profiles = self.media.GetProfiles()

        if not profiles:
            raise RuntimeError(
                "No ONVIF media profiles found"
            )

        self.profile_token = profiles[0].token

        self.log.info(
            "Connected to %s, profile=%s",
            self.name,
            self.profile_token
        )


    def disconnect(self):

        self.log.info(
            "Disconnecting %s",
            self.name
        )

        self.cam = None
        self.ptz = None
        self.media = None
        self.profile_token = None


    def _ensure_connected(self):

        if not self.ptz:
            self.connect()


    def get_state(self) -> CameraState:

        self._ensure_connected()

        status = self.ptz.GetStatus(
            {
                "ProfileToken": self.profile_token
            }
        )

        position = None

        if status.Position:

            position = PTZPosition(
                pan=status.Position.PanTilt.x,
                tilt=status.Position.PanTilt.y,
                zoom=(
                    status.Position.Zoom.x
                    if status.Position.Zoom
                    else None
                ),
            )

        moving = False
        
        if getattr(status, "MoveStatus", None):
            moving = (
                str(status.MoveStatus.PanTilt)
                != "IDLE"
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

        self._ensure_connected()

        current = self.get_state()

        if not current.position:
            raise RuntimeError(
                "Camera position unavailable"
            )

        current_x = current.position.pan
        current_y = current.position.tilt


        #
        # Thingino PTZ correction
        #
        # Camera movement direction is inverted.
        #
        target_x = pan - current_x
        target_y = current_y - tilt


        self.log.debug(
            "Move request pan=%s tilt=%s "
            "current=(%s,%s) delta=(%s,%s)",
            pan,
            tilt,
            current_x,
            current_y,
            target_x,
            target_y,
        )


        request = self.ptz.create_type(
            "RelativeMove"
        )

        request.ProfileToken = (
            self.profile_token
        )

        request.Translation = {
            "PanTilt": {
                "x": target_x,
                "y": target_y,
            }
        }

        self.ptz.RelativeMove(request)


    def stop(self):

        self._ensure_connected()

        request = self.ptz.create_type(
            "Stop"
        )

        request.ProfileToken = (
            self.profile_token
        )

        request.PanTilt = True
        request.Zoom = True

        self.ptz.Stop(request)


    def home(self):

        self._ensure_connected()

        request = self.ptz.create_type(
            "AbsoluteMove"
        )

        request.ProfileToken = (
            self.profile_token
        )

        request.Position = {
            "PanTilt": {
                "x": 0,
                "y": 0,
            }
        }

        self.ptz.AbsoluteMove(request)


    def goto_preset(self, preset):

        self._ensure_connected()

        request = self.ptz.create_type(
            "GotoPreset"
        )

        request.ProfileToken = (
            self.profile_token
        )

        request.PresetToken = str(
            preset
        )

        self.ptz.GotoPreset(request)


    def set_preset(self, preset, name):

        self._ensure_connected()

        request = self.ptz.create_type(
            "SetPreset"
        )

        request.ProfileToken = (
            self.profile_token
        )

        request.PresetToken = str(
            preset
        )

        request.PresetName = name

        self.ptz.SetPreset(request)
      
