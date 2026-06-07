import uuid
from pathlib import Path

def get_device_uuid():
    uuid_file = Path("device_uuid.txt")

    if not uuid_file.exists():
        uuid_file.write_text(str(uuid.uuid4()))

    return uuid_file.read_text().strip()


def readConfig(filename):
    sensor_type = None
    location = None
    gpio = None

    with open(filename, "r") as file:
        for line in file:
            parts = line.strip().split(": ", 1)

            if len(parts) != 2:
                continue

            key, value = parts

            if key == "Type":
                sensor_type = value

            elif key == "Location":
                location = value

            elif key == "GPIO":
                gpio = value

    return {
        "deviceUUID": get_device_uuid(),
        "sensorType": sensor_type,
        "locationName": location,
        "gpio": gpio
    }
