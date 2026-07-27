# PTZ Camera Bridge

A lightweight MQTT bridge that connects ONVIF PTZ cameras to Home Assistant.

The bridge is designed for installations where cameras are isolated on a dedicated network (for example behind a Frigate container) and exposes PTZ control through MQTT. It publishes the current camera position and movement state, accepts movement commands over MQTT, and automatically creates Home Assistant entities using MQTT Discovery.

## Features

* ONVIF PTZ camera support
* MQTT command interface
* Periodic state publishing (pan, tilt, zoom, moving)
* Home Assistant MQTT Discovery
* Supports multiple cameras
* Docker-friendly deployment

## MQTT Topics

Commands:

```text
home/camera/<camera>/command
```

State:

```text
home/camera/<camera>/state
```

Example command:

```json
{
  "action": "move",
  "pan": 30,
  "tilt": -10
}
```

## Current Status

The bridge currently supports **Thingino-based PTZ cameras** (tested with the **Sonoff PT2**) and has been designed so additional camera types can be added by implementing the common camera interface.

## Roadmap

* Additional camera implementations
* More Home Assistant entities (buttons, selects, numbers)
* Preset management
* Continuous movement support
* Camera capability discovery

## License

MIT
