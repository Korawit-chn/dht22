import time
import math
import requests
import sensorVPD
import board
import adafruit_dht
from datetime import datetime

NETWORK_LIST = "networkList.txt"
NETWORK_PORT = 5000
NETWORK_ROUTE = ""
NETWORK_RETRY_SECONDS = 60
READ_INTERVAL_SECONDS = 2
CLEANUP_DAYS = 30

sensorVPD.cache.init_db()

config = sensorVPD.configReader.readConfig("config.txt")
gpio = config.get("gpio")
sensor_type = config.get("sensorType")

base_url = None
sensor_id = None
last_network_check = 0

dht = None

if gpio:
    try:
        dht = adafruit_dht.DHT22(getattr(board, gpio))
    except Exception as e:
        print("Sensor initialization failed:", e)
else:
    if sensor_type == "DHT22":
        print("Warning: DHT22 requires GPIO configuration. Sensor reads will be disabled until GPIO is configured.")


def discover_backend():
    global base_url

    try:
        new_url = sensorVPD.network.networkSearch(NETWORK_LIST, NETWORK_PORT, NETWORK_ROUTE)

        if new_url != base_url:
            if new_url:
                print("Backend discovered:", new_url)
            else:
                print("Backend unavailable")

        base_url = new_url

    except Exception as e:
        print("Backend discovery error:", e)
        base_url = None


def register_sensor_if_needed():
    global sensor_id

    if base_url is None or sensor_id is not None:
        return

    try:
        register_url = f"{base_url}/api/registerSensor"
        r = requests.post(register_url, json=config, timeout=5)
        r.raise_for_status()
        response = r.json()

        sensor_id = response.get("sensorID")

        if sensor_id:
            print(f"Registered sensor ID: {sensor_id}")
        else:
            print("Registration response did not include sensorID")

    except Exception as e:
        print("Registration failed:", e)


def flush_queue():
    if base_url is None or sensor_id is None:
        return

    data_url = f"{base_url}/api/getDataDHT"
    rows = sensorVPD.cache.get_unsent()

    for row in rows:
        payload = {
            "sensorID": sensor_id,
            "temperature": row["temperature"],
            "humidity": row["humidity"],
            "VPD": row["vpd"],
            "time": row["timestamp"]
        }

        try:
            r = requests.post(data_url, json=payload, timeout=5)

            if r.status_code == 200:
                sensorVPD.cache.mark_uploaded(row["id"])
                print(f"Uploaded record {row['id']} at {row['timestamp']}")
            else:
                print(f"Upload failed for record {row['id']}: {r.status_code} {r.text}")
                break

        except Exception as e:
            print(f"Upload error for record {row['id']}:", e)
            break


def maybe_refresh_network():
    global last_network_check
    now = time.time()

    if now - last_network_check >= NETWORK_RETRY_SECONDS:
        discover_backend()
        register_sensor_if_needed()
        flush_queue()
        sensorVPD.cache.cleanup(CLEANUP_DAYS)
        last_network_check = now


def read_sensor():
    if dht is None:
        raise RuntimeError("No sensor configured")

    temperature = dht.temperature
    humidity = dht.humidity

    if temperature is None or humidity is None:
        raise RuntimeError("Sensor returned invalid values")

    vpd = (
        0.6108
        * math.exp((17.27 * temperature) / (temperature + 237.3))
        * (1 - (humidity / 100))
    )

    return temperature, humidity, vpd


while True:
    maybe_refresh_network()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        temperature, humidity, vpd = read_sensor()
        sensorVPD.cache.save_reading(timestamp, temperature, humidity, vpd)

        print(
            f"{timestamp} ({gpio}) Temp: {temperature:.1f}°C "
            f"Humidity: {humidity:.1f}% VPD: {vpd:.2f}kPa "
            f"Saved locally"
        )

        register_sensor_if_needed()
        flush_queue()

    except RuntimeError as error:
        print(f"{timestamp} ({gpio}) Reading error:", error)

    except Exception as e:
        print(f"{timestamp} ({gpio}) Error:", e)

    time.sleep(READ_INTERVAL_SECONDS)
