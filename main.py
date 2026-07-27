#!/usr/bin/env python3

import logging
import signal
import sys

from config import Config
from mqtt import MQTTBridge
from thingino import ThinginoCamera


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


def build_cameras(config):
    cameras = {}

    for name, camera_cfg in config.cameras.items():
        cameras[name] = ThinginoCamera(
            name=name,
            host=camera_cfg["host"],
            port=camera_cfg.get("port", 80),
            username=camera_cfg["username"],
            password=camera_cfg["password"],
        )

    return cameras


def main():
    setup_logging()

    log = logging.getLogger("main")

    config = Config("config.yaml")

    cameras = build_cameras(config)

    bridge = MQTTBridge(
        broker=config.mqtt.host,
        port=config.mqtt.port,
        username=config.mqtt.username,
        password=config.mqtt.password,
        topic_prefix=config.mqtt.topic_prefix,
        cameras=cameras,
    )

    def shutdown(*_):
        log.info("Stopping PTZ bridge...")
        bridge.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log.info("Starting MQTT PTZ bridge")
    bridge.run()


if __name__ == "__main__":
    main()
