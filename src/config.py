#!/usr/bin/env python3
# config.py
#
# Configuration loader for the MQTT PTZ bridge.
#
# Reads the YAML configuration file, validates required settings,
# and exposes the parsed configuration as strongly typed dataclasses.

from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class MQTTConfig:
    """
    MQTT broker configuration.
    """
    host: str
    port: int = 1883
    username: str | None = None
    password: str | None = None
    topic_prefix: str = "home/camera"


@dataclass
class CameraConfig:
    """
    Configuration for a single camera.
    """
    name: str
    type: str
    host: str
    port: int
    username: str
    password: str
    manufacturer: str
    model: str


class Config:
    """
    Loads and validates the bridge configuration.

    The configuration is read once during startup.
    """

    def __init__(self, filename="config.yaml"):
        self.filename = Path(filename)

        if not self.filename.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.filename}"
            )

        self._load()

    def _load(self):
        """
        Load and validate the YAML configuration.
        """

        with self.filename.open(
            "r",
            encoding="utf-8",
        ) as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError("Empty configuration file")

        self.mqtt = self._load_mqtt(data.get("mqtt", {}))
        self.cameras = self._load_cameras(data.get("cameras", {}))


    def _load_mqtt(
        self,
        data: dict,
    ) -> MQTTConfig:
        """
        Parse the MQTT configuration section.
        """
        required = ["host"]

        for item in required:
            if item not in data:
                raise ValueError(
                    f"Missing MQTT configuration value: {item}"
                )

        return MQTTConfig(
            host=data["host"],
            port=data.get("port", 1883),
            username=data.get("username"),
            password=data.get("password"),
            topic_prefix=data.get(
                "topic_prefix",
                "home/camera"
            ),
        )


    def _load_cameras(
        self,
        data: dict,
    ) -> dict[str, CameraConfig]:
        """
        Parse all configured cameras.
        """
        cameras = {}

        for name, cfg in data.items():

            required = [
                "type",
                "host",
                "username",
                "password",
            ]

            for field in required:
                if field not in cfg:
                    raise ValueError(
                        f"Camera '{name}' missing '{field}'"
                    )

            cameras[name] = CameraConfig(
                name=cfg.get("name", name),
                type=cfg["type"],
                host=cfg["host"],
                port=cfg.get("port", 80),
                username=cfg["username"],
                password=cfg["password"],
                manufacturer=cfg.get("manufacturer", "Unknown"),
                model=cfg.get("model", "Unknown"),
            )

        if not cameras:
            raise ValueError(
                "No cameras configured"
            )

        return cameras
