#!/usr/bin/env python3
# mqtt.py
"""
MQTT bridge between camera implementations and Home Assistant.

Handles:
- MQTT command reception
- Camera state publishing
- Home Assistant discovery
- Periodic camera state monitoring
"""

import json
import logging
import threading
import time
import paho.mqtt.client as mqtt

from discovery import DiscoveryPublisher

class MQTTBridge:
    """
    Handles MQTT communication between Home Assistant
    and PTZ cameras.

    Responsibilities:
    - Subscribe to camera command topics
    - Execute PTZ commands
    - Publish camera state
    - Publish Home Assistant MQTT Discovery messages
    - Monitor camera state changes
    """
    # Normal camera position refresh interval
    STATE_POLL_INTERVAL = 5

    # Faster refresh while camera is moving
    # for smoother Home Assistant updates
    MOVING_POLL_INTERVAL = 0.1

    def __init__(
        self,
        broker,
        port,
        username,
        password,
        topic_prefix,
        cameras,
    ):
        """
        Initialize the MQTT bridge.
    
        Args:
            broker: MQTT broker hostname or IP address.
            port: MQTT broker port.
            username: Optional MQTT username.
            password: Optional MQTT password.
            topic_prefix: Base MQTT topic for camera messages.
            cameras: Dictionary containing configured cameras.
        """


        self.log = logging.getLogger(__name__)

        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix.rstrip("/")

        self.cameras = cameras

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1
        )

        if username:
            self.client.username_pw_set(
                username,
                password,
            )

        self.client.on_connect = (
            self._on_connect
        )

        self.client.on_message = (
            self._on_message
        )

        self.state_cache = {}
        self.poll_thread = None
        self.running = False

        self.discovery = DiscoveryPublisher(
            self.client,
            self.topic_prefix,
        )

        self.presets = {}


    def run(self):
        """
        Connect to MQTT and start the event loop.
    
        The MQTT network loop runs in the current thread.
        Incoming messages are handled through callbacks.
        """
        self.log.info(
            "Connecting to MQTT %s:%s",
            self.broker,
            self.port,
        )

        self.client.connect(
            self.broker,
            self.port,
            60,
        )

        self.running = True

        self.client.loop_forever()


    def stop(self):
        """
        Stop the MQTT bridge gracefully.
    
        Disconnects from the broker and stops state monitoring.
        """
        self.log.info(
            "Stopping MQTT bridge"
        )

        self.running = False

        self.client.disconnect()


    def _on_connect(
        self,
        _client,
        _userdata,
        _flags,
        rc,
    ):
        """
        MQTT connection callback.
    
        Called by paho after connection establishment.
        Subscribes to command topics and initializes cameras.
        """
        if rc != 0:
            self.log.error(
                "MQTT connection failed: %s",
                rc,
            )
            return


        self.log.info(
            "Connected to MQTT"
        )

        topic = (
            f"{self.topic_prefix}/+/command"
        )

        self.client.subscribe(topic)

        self.log.info(
            "Subscribed to %s",
            topic,
        )

        # Connect cameras after MQTT is ready
        for camera in self.cameras.values():
            self._connect_camera(camera)
            self.discovery.publish_camera(camera)

        self.poll_thread = threading.Thread(
            target=self._state_monitor_loop,
            daemon=True,
        )
        self.poll_thread.start()

    def _on_message(
        self,
        _client,
        _userdata,
        msg,
    ):
        """
        Handle incoming MQTT commands.
    
        Expected topic format:
    
            <topic_prefix>/<camera_name>/command
    
        Example:
    
            home/camera/sonoff_pt2/command
        """
        try:

            payload = json.loads(
                msg.payload.decode()
            )

        except Exception:

            self.log.error(
                "Invalid JSON: %s",
                msg.payload,
            )

            return

        try:
            camera_name = msg.topic.split("/")[2]
        except IndexError:
            return

        camera = self.cameras.get(
            camera_name
        )


        if not camera:

            self.log.warning(
                "Unknown camera: %s",
                camera_name,
            )

            return


        try:

            self.handle_command(
                camera,
                payload,
            )


        except Exception:

            self.log.exception(
                "Command failed"
            )


    def handle_command(
        self,
        camera,
        command,
    ):
        """
        Execute a PTZ command on a camera.
    
        Supported actions:
        - move
        - stop
        - home
        - preset
        - set_preset
        """
        action = command.get(
            "action"
        )


        self.log.debug(
            "Camera %s action %s",
            camera.name,
            action,
        )

        handled = True
        if action == "move":

            camera.move(
                pan=command.get(
                    "pan",
                    0,
                ),
                tilt=command.get(
                    "tilt",
                    0,
                ),
                zoom=command.get(
                    "zoom",
                    0,
                ),
            )


        elif action == "stop":

            camera.stop()


        elif action == "home":

            camera.home()


        elif action == "preset":

            camera.goto_preset(
                command["preset"]
            )

        elif action == "set_preset":

            name = command.get("name")

            if not name:
                raise ValueError(
                    "set_preset requires 'name'"
                )

            camera.set_preset(name)

        else:
            handled = False
            self.log.warning(
                "Unknown action: %s",
                action,
            )

        if handled:
            self.publish_state(camera)

    def publish_state(self, camera, state=None):
        """
        Publish the current camera state.
    
        The state is published as retained MQTT data so
        Home Assistant receives the last known position
        after a restart.
        """
        if state is None:
            state = camera.get_state()

        self.state_cache[camera.name] = state

        payload = {
            "moving": state.moving,
        }

        if state.position:

            payload.update(
                {
                    "pan": state.position.pan,
                    "tilt": state.position.tilt,
                    "zoom": state.position.zoom,
                }
            )


        topic = (
            f"{self.topic_prefix}/"
            f"{camera.name}/state"
        )


        self.client.publish( topic, json.dumps(payload), qos=1, retain=True, )

        self.log.debug(
            "%s pan=%s tilt=%s moving=%s",
            camera.name,
            state.position.pan if state.position else None,
            state.position.tilt if state.position else None,
            state.moving,
        )

    def _connect_camera(self, camera):

        try:
            camera.connect()

            # Publish initial state
            state = camera.get_state()
            self.publish_state(camera, state)

            # Publish preset selector if supported
            presets = camera.get_presets()

            if presets:
                self.discovery.publish_select(
                    camera,
                    presets,
                )

        except Exception:
            self.log.exception(
                "Camera connection failed: %s",
                camera.name,
            )

    def _state_monitor_loop(self):
        """
        Background thread monitoring camera positions.
    
        Polling interval is dynamic:
        - normal: every STATE_POLL_INTERVAL seconds
        - while moving: every MOVING_POLL_INTERVAL seconds
        """

        self.log.info(
            "Starting camera state monitor"
        )

        while self.running:

            for camera in self.cameras.values():
                try:
                    state = camera.get_state()
                    previous = self.state_cache.get(camera.name)
                    if previous != state:
                        self.log.debug(
                            "State change detected for %s",
                            camera.name,
                        )
                        self.publish_state(camera, state)
                except Exception:
                    self.log.exception(
                        "Polling %s failed",
                        camera.name,
                    )

            delay = self.STATE_POLL_INTERVAL  

            if any(
                s and s.moving
                for s in self.state_cache.values()
            ):
                delay = self.MOVING_POLL_INTERVAL 

            self.log.debug(
                "State monitor cycle completed"
            )

            time.sleep(delay)
