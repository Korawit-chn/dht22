import json
import uuid
from pathlib import Path


def get_device_uuid():
    uuid_file = Path("device_uuid.txt")

    if not uuid_file.exists():
        uuid_file.write_text(str(uuid.uuid4()))

    return uuid_file.read_text().strip()


def readConfig(filename):
    with open(filename, "r") as file:
        config_data = json.load(file)

    sensor_type = config_data.get("Type") or config_data.get("sensorType") or config_data.get("type")
    location = config_data.get("Location") or config_data.get("locationName") or config_data.get("location")
    gpio = config_data.get("GPIO") or config_data.get("gpio")
    description = config_data.get("description") or config_data.get("Description") or config_data.get("desc")

    return {
        "deviceUUID": get_device_uuid(),
        "sensorType": sensor_type,
        "locationName": location,
        "gpio": gpio,
        "description": description,
    }
