# Implement Offline-First Data Collection with SQLite Cache

## Objective

Refactor the Raspberry Pi sensor client to support offline operation.

The sensor must continue collecting data even when the backend server is unavailable. Data should be stored locally in SQLite and automatically synchronized when connectivity is restored.

---

# Current Behavior

Current startup flow:

1. Search for backend server.
2. Register sensor.
3. Start collecting data.
4. If server cannot be found, terminate program.

This causes data loss when:

* WiFi is unavailable
* Backend is offline
* Database is offline
* Network discovery fails during startup

---

# New Required Behavior

The sensor program must never stop collecting data because of network issues.

Required flow:

```text
Start
│
├─ Initialize SQLite cache
│
├─ Load config
│
├─ Initialize sensor
│
└─ Main Loop
     │
     ├─ Read sensor
     │
     ├─ Save reading to SQLite
     │
     ├─ Check network periodically
     │
     ├─ Register sensor if needed
     │
     ├─ Upload pending data if connected
     │
     │
     └─ Sleep
```

---

# Project Structure

Create a new module:

```text
sensorVPD/
│
├── cache.py
├── configReader.py
├── network.py
└── ...
```

SQLite database file:

```text
sensor_cache.db
```

should be automatically created if missing.

---

# SQLite Requirements

Create table:

```sql
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    vpd REAL,
    uploaded INTEGER DEFAULT 0
);
```

---

# cache.py Requirements

Implement functions:

```python
init_db()

save_reading(
    timestamp,
    temperature,
    humidity,
    vpd
)

get_unsent()

mark_uploaded(record_id)

cleanup(days=30)
```

Behavior:

* save_reading() inserts a row.
* get_unsent() returns rows where uploaded = 0.
* mark_uploaded() sets uploaded = 1.
* cleanup() removes uploaded rows older than retention period.

---

# Network Discovery

Current code only searches once.

Replace with retry behavior.

Requirements:

* Attempt network discovery every 60 seconds.
* Program must continue running if server is unavailable.
* Do not terminate application because network discovery fails.

Example state:

```python
base_url = None
sensor_id = None
```

---

# Sensor Registration

Current endpoint:

```http
POST /api/registerSensor
```

Payload:

```json
{
  "deviceUUID": "...",
  "sensorType": "...",
  "locationName": "...",
  "gpio": "D17"
}
```

Requirements:

* Registration should be retried whenever connectivity returns.
* Store returned sensorID in memory.
* Do not terminate application if registration fails.
* Retry during future network checks.

---

# Upload Queue

Implement function:

```python
flush_queue(data_url, sensor_id)
```

Behavior:

1. Read all records where uploaded = 0.
2. Send oldest first.
3. If upload succeeds:

   * mark row uploaded.
4. If upload fails:

   * stop processing.
   * leave remaining rows unchanged.

Data must never be deleted before successful upload.

---

# Data Retention

Local database acts as:

1. Upload queue
2. Historical backup

Requirements:

* Uploaded records remain in SQLite.
* Keep backup for configurable retention period.
* Default retention = 30 days.
* cleanup() should remove only:

  * uploaded records
  * older than retention period

Never delete unsent records.

---

# Sensor Reading Flow

For every successful sensor reading:

1. Read sensor.
2. Calculate VPD.
3. Save reading to SQLite immediately.
4. Attempt upload if connected.

Local save must happen before network operations.

This guarantees no data loss.

---

# Error Handling

Requirements:

* Sensor read errors should not terminate program.
* Network errors should not terminate program.
* Registration errors should not terminate program.
* Upload errors should not terminate program.
* SQLite errors should be logged.

Application should run indefinitely.

---

# GPIO Handling

Configuration may contain:

```text
GPIO: D17
```

or omit GPIO completely.

Example:

```text
Type: C5A
Location: Outside Dome 1
```

Requirements:

* GPIO is optional.
* DHT22 requires GPIO.
* Other sensor types may not.
* Do not assume GPIO always exists.

---

# Configuration Format

Current format:

```text
Type: DHT22
Location: Outside Dome 1
GPIO: D17
```

configReader should return:

```python
{
    "deviceUUID": "...",
    "sensorType": "DHT22",
    "locationName": "Outside Dome 1",
    "gpio": "D17"
}
```

If GPIO is missing:

```python
{
    "deviceUUID": "...",
    "sensorType": "C5A",
    "locationName": "Outside Dome 1",
    "gpio": None
}
```

---

# Success Criteria

The sensor application must:

* Continue collecting data with no network.
* Continue collecting data with no backend.
* Continue collecting data with no database server.
* Automatically reconnect when backend becomes available.
* Automatically register sensor when connectivity returns.
* Upload cached readings in chronological order.
* Keep local backup history.
* Prevent data loss during outages.
* Run unattended for long periods on Raspberry Pi.
