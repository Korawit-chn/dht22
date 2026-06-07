import time
import math
import requests
import sensorVPD
import board
import adafruit_dht
from datetime import datetime

# Find server
base_url = sensorVPD.network.networkSearch("networkList.txt", 5000, "")

# Read config
config = sensorVPD.configReader.readConfig("config.txt")

gpio = config.get("gpio")

if gpio is None:
    pass

if base_url is None:
    print("No server found")
    exit()

# DHT22 Sensor
dht = adafruit_dht.DHT22(getattr(board, gpio))

try:
    # Register sensor
    register_url = f"{base_url}/api/registerSensor"

    r = requests.post(
        register_url,
        json=config,
        timeout=5
    )

    r.raise_for_status()

    response = r.json()

    sensor_id = response["sensorID"]

    print(f"Registered sensor ID: {sensor_id}")

except Exception as e:
    print("Registration failed:", e)
    exit()

# Data upload endpoint
data_url = f"{base_url}/api/getDataDHT"

while True:

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        temperature = dht.temperature
        humidity = dht.humidity

        vpd = (
            0.6108
            * math.exp((17.27 * temperature) / (temperature + 237.3))
            * (1 - (humidity / 100))
        )

        data = {
            "sensorID": sensor_id,
            "temperature": temperature,
            "humidity": humidity,
            "VPD": vpd,
            "time": timestamp
        }

        r = requests.post(
            data_url,
            json=data,
            timeout=5
        )

        print(
            f"{timestamp} ({gpio}) "
            f"Temp: {temperature:.1f}°C "
            f"Humidity: {humidity:.1f}% "
            f"VPD: {vpd:.2f}kPa "
            f"POST: {r.status_code}"
        )

        if r.status_code != 200:
            print("Upload failed:", r.text)

    except RuntimeError as error:
        print(f"{timestamp} ({gpio}) Reading error:", error)

    except Exception as e:
        print("Error:", e)

    time.sleep(2)
