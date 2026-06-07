import serial
import time
import math
import requests
from datetime import datetime

import sensorVPD

NETWORK_LIST = "networkList.txt"
NETWORK_PORT = 5000
NETWORK_ROUTE = ""
NETWORK_RETRY_SECONDS = 60
READ_INTERVAL_SECONDS = 1.1
CLEANUP_DAYS = 30

sensorVPD.cache.init_db()
config = sensorVPD.configReader.readConfig("config.txt")

base_url = None
sensor_id = None
last_network_check = 0

payload = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x05])


def modbus_crc(data: bytes):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, "little")


def temp_convert(data: bytes):
    binary = format(int(data, 16), "016b")
    sign = binary[1]

    if sign == "1":
        value = -((int("".join("1" if x == "0" else "0" for x in binary), 2) + 1))
    else:
        value = int(binary, 2)

    return value


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

    data_url = f"{base_url}/api/getDataC5A"
    rows = sensorVPD.cache.get_unsent()

    for row in rows:
        payload_data = {
            "sensorID": sensor_id,
            "windSpeed": row["windspeed"],
            "windDirection": row["windDirection"],
            "temperature": row["temperature"],
            "humidity": row["humidity"],
            "VPD": row["vpd"],
            "time": row["timestamp"]
        }

        try:
            r = requests.post(data_url, json=payload_data, timeout=5)

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


try:
    ser = serial.Serial(
        port="/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0",
        baudrate=9600,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=2,
    )
except Exception as e:
    print("Serial initialization failed:", e)
    ser = None

frame = payload + modbus_crc(payload)
print("Send:", frame.hex(" "))
print("---------------------------------------------------")

while True:
    maybe_refresh_network()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if ser is None:
            raise RuntimeError("Serial port not available")

        ser.write(frame)
        time.sleep(1.1)
        response = ser.read(20)

        data = response[3:11]
        wind_speed = int.from_bytes(data[0:2], "big") * 0.01
        wind_direction = int.from_bytes(data[2:4], "big")
        temperature = temp_convert(data[4:6].hex().upper()) * 0.1
        humidity = int.from_bytes(data[6:8], "big") * 0.1
        vpd = 0.6108 * math.exp((17.27 * temperature) / (temperature + 237.3)) * (1 - (humidity / 100))

        sensorVPD.cache.save_reading(
            timestamp,
            temperature,
            humidity,
            vpd,
            windspeed=wind_speed,
            windDirection=wind_direction,
            sensor_id=sensor_id,
        )

        print(f"{timestamp} Temp: {temperature:.1f}°C Humidity: {humidity:.1f}% VPD: {vpd:.1f}kPa Saved locally")

        register_sensor_if_needed()
        flush_queue()

    except Exception as e:
        print("Error Occur", e)

    time.sleep(READ_INTERVAL_SECONDS)



