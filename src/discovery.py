#!/usr/bin/env python3
"""
Home Assistant MQTT Discovery publisher.

Publishes MQTT Discovery configuration for all supported PTZ camera entities.
Currently exposes:

- Pan sensor
- Tilt sensor
- Moving binary sensor
"""

import json


class DiscoveryPublisher:
    """
    Publishes Home Assistant MQTT Discovery messages.

    One device is created per camera, with all entities grouped under it.
    """

    DISCOVERY_PREFIX = "homeassistant"

    def __init__(self, mqtt_client, topic_prefix):
        """
        Initialize the discovery publisher.

        Args:
            mqtt_client: Connected Paho MQTT client.
            topic_prefix: Base MQTT topic used for camera communication.
        """
        self.client = mqtt_client
        self.topic_prefix = topic_prefix.rstrip("/")

    def publish_camera(self, camera):
        """
        Publish MQTT Discovery configuration for a camera.

        Args:
            camera: Camera implementation.
        """
        device = {
            "identifiers": [f"ptz_{camera.name}"],
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

    def _state_topic(self, camera):
        """Return the MQTT state topic for a camera."""
        return f"{self.topic_prefix}/{camera.name}/state"

    def _publish_sensor(
        self,
        camera,
        key,
        name,
        value_template,
        unit,
        device,
    ):
        """
        Publish a numeric sensor.

        Args:
            camera: Camera instance.
            key: Entity identifier suffix.
            name: Friendly entity name.
            value_template: Home Assistant value template.
            unit: Unit of measurement.
            device: Home Assistant device description.
        """
        topic = (
            f"{self.DISCOVERY_PREFIX}/sensor/"
            f"{camera.name}_{key}/config"
        )

        payload = {
            "name": f"{camera.name.title()} {name}",
            "unique_id": f"ptz_{camera.name}_{key}",
            "state_topic": self._state_topic(camera),
            "value_template": value_template,
            "unit_of_measurement": unit,
            "icon": "mdi:axis-arrow",
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
        """
        Publish a binary sensor.

        Args:
            camera: Camera instance.
            key: Entity identifier suffix.
            name: Friendly entity name.
            value_template: Home Assistant value template.
            device: Home Assistant device description.
        """
        topic = (
            f"{self.DISCOVERY_PREFIX}/binary_sensor/"
            f"{camera.name}_{key}/config"
        )

        payload = {
            "name": f"{camera.name.title()} {name}",
            "unique_id": f"ptz_{camera.name}_{key}",
            "state_topic": self._state_topic(camera),
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
