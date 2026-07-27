#!/usr/bin/env python3

import json
import logging
import threading

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

        self.client = mqtt.Client()

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
            try:
                camera.connect()

            except Exception:
                self.log.exception(
                    "Camera connection failed: %s",
                    camera.name,
                )


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


    def publish_state(
        self,
        camera,
    ):

        state = camera.get_state()

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


        self.client.publish(
            topic,
            json.dumps(payload),
            retain=True,
        )
