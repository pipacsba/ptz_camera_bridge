#!/usr/bin/env python3
# mqtt.py

import json
import logging
import threading
import time

import paho.mqtt.client as mqtt


class MQTTBridge:

    def __init__(
        self,
        broker,
        port,
        username,
        password,
        topic_prefix,
        cameras,
    ):

        self.log = logging.getLogger("mqtt")

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


    def run(self):

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

        self.log.info(
            "Stopping MQTT bridge"
        )

        self.running = False

        self.client.disconnect()


    def _on_connect(
        self,
        client,
        userdata,
        flags,
        rc,
    ):

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
        
        self.poll_thread = threading.Thread(
            target=self._state_monitor_loop,
            daemon=True,
        )
        self.poll_thread.start()

    def _on_message(
        self,
        client,
        userdata,
        msg,
    ):

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


        parts = msg.topic.split("/")

        # expected:
        # home/camera/front/command

        if len(parts) < 4:
            return


        camera_name = parts[-2]


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

        action = command.get(
            "action"
        )


        self.log.info(
            "Camera %s action %s",
            camera.name,
            action,
        )


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

            camera.set_preset(
                command["preset"],
                command.get(
                    "name",
                    "",
                ),
            )


        else:

            self.log.warning(
                "Unknown action: %s",
                action,
            )


        self.publish_state(
            camera
        )


    def publish_state(self, camera, state=None):

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
    
            state = camera.get_state()
            self.publish_state(camera, state)
    
        except Exception:
            self.log.exception(
                "Camera connection failed: %s",
                camera.name,
            )

    def _state_monitor_loop(self):
    
        while self.running:
    
            for camera in self.cameras.values():
    
                try:
    
                    state = camera.get_state()
    
                    previous = self.state_cache.get(camera.name)
    
                    if previous != state:
    
                        self.publish_state(camera, state)
    
                except Exception:
    
                    self.log.exception(
                        "Polling %s failed",
                        camera.name,
                    )
    
            delay = 5
            
            if any(
                s and s.moving
                for s in self.state_cache.values()
            ):
                delay = 0.2
            
            time.sleep(delay)
