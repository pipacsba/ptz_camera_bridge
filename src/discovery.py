#!/usr/bin/env python3
# discovery.py

import json


class DiscoveryPublisher:

    def __init__(self, mqtt_client, topic_prefix):
        self.client = mqtt_client
        self.topic_prefix = topic_prefix.rstrip("/")


    def publish_camera(self, camera):

        device = {
            "identifiers": [
                f"ptz_{camera.name}"
            ],
            "name": camera.name.replace("_", " ").title(),
            "manufacturer": camera.manufacturer,
            "model": camera.model,
        }

        self._publish_sensor(
            camera,
            "pan",
            "Pan",
            "{{ value_json.pan }}",
            "°",
            device,
        )

        self._publish_sensor(
            camera,
            "tilt",
            "Tilt",
            "{{ value_json.tilt }}",
            "°",
            device,
        )

        self._publish_binary_sensor(
            camera,
            "moving",
            "Moving",
            "{{ value_json.moving }}",
            device,
        )


    def _publish_sensor(
        self,
        camera,
        key,
        name,
        value_template,
        unit,
        device,
    ):

        topic = (
            f"homeassistant/sensor/"
            f"{camera.name}_{key}/config"
        )

        payload = {
            "name": f"{camera.name.title()} {name}",
            "unique_id": f"ptz_{camera.name}_{key}",
            "state_topic": (
                f"{self.topic_prefix}/"
                f"{camera.name}/state"
            ),
            "value_template": value_template,
            "unit_of_measurement": unit,
            "device": device,
        }

        self.client.publish(
            topic,
            json.dumps(payload),
            qos=1,
            retain=True,
        )


    def _publish_binary_sensor(
        self,
        camera,
        key,
        name,
        value_template,
        device,
    ):

        topic = (
            f"homeassistant/binary_sensor/"
            f"{camera.name}_{key}/config"
        )

        payload = {
            "name": f"{camera.name.title()} {name}",
            "unique_id": f"ptz_{camera.name}_{key}",
            "state_topic": (
                f"{self.topic_prefix}/"
                f"{camera.name}/state"
            ),
            "value_template": value_template,
            "payload_on": "true",
            "payload_off": "false",
            "device": device,
        }

        self.client.publish(
            topic,
            json.dumps(payload),
            qos=1,
            retain=True,
        )
