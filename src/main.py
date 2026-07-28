#!/usr/bin/env python3
# main.py

import logging
import signal
import sys

from config import Config
from mqtt import MQTTBridge
from thingino import ThinginoCamera
from discovery import DiscoveryPublisher

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        force=True,
    )


def build_cameras(config):
    cameras = {}

    for name, camera_cfg in config.cameras.items():

        if camera_cfg.type == "thingino":

            cameras[name] = ThinginoCamera(
                name=name,
                host=camera_cfg.host,
                port=camera_cfg.port,
                username=camera_cfg.username,
                password=camera_cfg.password,
                manufacturer=camera_cfg.manufacturer,
                model=camera_cfg.model,
            )

        else:
            raise ValueError(
                f"Unsupported camera type: {camera_cfg.type}"
            )

    return cameras


def main():
    setup_logging()

    log = logging.getLogger("main")

    try:
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

    except Exception:
        log.exception("Failed to initialize PTZ bridge")
        sys.exit(1)


    def shutdown(*_):
        log.info("Stopping PTZ bridge...")
        bridge.stop()
        sys.exit(0)


    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)


    log.info(
        "Starting MQTT PTZ bridge with %d camera(s)",
        len(cameras)
    )

    for name in cameras:
        log.info("Configured camera: %s", name)

    bridge.run()


if __name__ == "__main__":
    main()
