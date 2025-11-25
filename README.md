**IoT → Kafka → HDFS → Frontend**

This repository contains a small end-to-end demo that reads sensor data from an Android device, publishes it to Kafka, persists messages into HDFS, and serves a simple Flask frontend that reads stored JSON files from HDFS and visualizes accelerometer and gyroscope values using Chart.js.

**This README covers:**
- Project overview and architecture
- Files and services created
- Installation and run commands (CLI + docker-compose)
- Frontend API and how the charts work
- Troubleshooting and next steps

**Architecture**
- **IoT device**: publishes sensor readings (accelerometer / gyroscope). Messages appear in two common forms in logs or broker output:
  - `Buffered: {'type': 'android.sensor.accelerometer', 'values': [...], 'timestamp': 984...}`
  - `MQTT: android/sensor {"type":"android.sensor.accelerometer","values":[...],"timestamp":984...}`
- **Kafka**: topic `sensors` receives the messages.
- **Consumer (Python)**: `scripts/k.py` (or similar consumer) reads Kafka and writes messages to HDFS using WebHDFS. Files are placed under HDFS path `/iot/sensors` (with date subfolders such as `date=YYYY-MM-DD`). Example HDFS file: `/iot/sensors/date=2025-11-25/data.json`.
- **HDFS**: Namenode and Datanodes run in Docker. HDFS Web UI is exposed at `http://namenode:9870`.
- **Frontend (Flask + Chart.js)**: service reads files from HDFS using `hdfs.InsecureClient('http://namenode:9870', user='root')`. It exposes API endpoints and serves a static UI that plots Accel/Gyro series.

**Repository layout (relevant files)**
- `docker-compose.yml` — services: zookeeper, kafka, namenode, datanode1, datanode2, python-client, frontend
- `scripts/k.py` — Kafka consumer that writes messages to HDFS (example consumer provided earlier)
- `scripts/frontend/app.py` — Flask backend that lists and parses HDFS JSON files; endpoints: `/api/files`, `/api/data`, `/api/latest_file_points`, `/`
- `scripts/frontend/requirements.txt` — Python dependencies for frontend (Flask, hdfs)
- `scripts/frontend/templates/index.html` — frontend HTML
- `scripts/frontend/static/js/app.js` — frontend JS (Chart.js visualization + polling)
- `scripts/frontend/static/css/style.css` — small UI styles

**Ports used**
- `9092` — Kafka broker
- `2181` — Zookeeper
- `9870` — HDFS Namenode Web UI (WebHDFS)
- `5000` — Frontend UI (mapped from container to host by docker-compose)

**How data flows (quick)**
1. Device publishes sensor messages to MQTT/Kafka.
2. A Kafka consumer (Python) reads the message and writes it to HDFS as JSON.
3. HDFS stores the messages under `/iot/sensors` with date partitioning (example: `date=2025-11-25/data.json`).
4. The Flask frontend queries the HDFS WebHDFS API, reads JSON files, parses messages, and serves data via REST endpoints. The UI fetches these endpoints and draws charts using Chart.js.

**Quick start (Docker-compose recommended)**
1. From the repository root start the stack (starts HDFS, Kafka, etc.):

```pwsh
docker compose up -d
```

2. Confirm containers are running:

```pwsh
docker compose ps
```

3. (Optional) Confirm namenode Web UI is available: open `http://localhost:9870`.

4. Start the frontend via docker-compose (this project includes a `frontend` service which runs the Flask app and maps container port 5000 to host 5000):

```pwsh
docker compose up -d frontend
```

5. Open the UI in your browser:

  - `http://localhost:5000`

**Quick start (ad-hoc / debugging using `python-client` container)**
- You can also run or test the frontend inside the existing `python-client` container.

Open a shell in the python client container:

```pwsh
docker exec -it python-client bash
```

Install dependencies (only inside container; the docker-compose frontend service already installs them on startup):

```bash
pip install -r /scripts/frontend/requirements.txt
```

Run the Flask app directly (development server):

```bash
python /scripts/frontend/app.py
```

Then open `http://localhost:5000` on the host. Note: if you run directly in the `python-client` container you must ensure the container was started with a port mapping (or run it inside the `python-client` container and curl from the container as described below).

**Important CLI commands used while developing and debugging**
- Enter python container shell: `docker exec -it python-client bash`
- Install frontend deps inside container: `pip install -r /scripts/frontend/requirements.txt`
- Start frontend manually: `python /scripts/frontend/app.py`
- Start frontend with compose: `docker compose up -d frontend`
- Tail frontend logs: `docker compose logs --follow --tail=200 frontend`
- Query frontend API from host: `curl http://localhost:5000/api/latest_file_points?count=20`
- Query API from inside frontend container: `docker compose exec frontend bash -lc "curl -sS 'http://127.0.0.1:5000/api/latest_file_points?count=20'"`
- Inspect HDFS folder via WebHDFS API (from inside frontend container):
  - `curl -i 'http://namenode:9870/webhdfs/v1/iot/sensors?op=LISTSTATUS'`
  - `curl -sS 'http://namenode:9870/webhdfs/v1/iot/sensors/date=2025-11-25/data.json?op=OPEN' | head -c 1200`

**Frontend APIs**
- `GET /` — UI page (HTML + Chart.js)
- `GET /api/files` — returns discovered HDFS JSON files with paths and modification times. Example result:

```json
[
  {"path":"/iot/sensors/date=2025-11-25/data.json","mtime":1764052925885}
]
```

- `GET /api/data?count=N` — returns up to the last N parsed messages across files (chronological). Each item looks like:

```json
{
  "ts": 985947898,
  "accel": {"x": -0.069, "y": 1.056, "z": 10.777},
  "gyro": null
}
```

- `GET /api/latest_file_points?count=N` — returns the last N messages from the newest file only (chronological). This is convenient for live-like plotting.

Note: The Flask backend normalizes message shapes and supports messages in several forms: JSON arrays, newline-delimited JSON, and prefixed lines like `Buffered:` or `MQTT:` with Python-style single-quoted dicts (the parser attempts to convert them). It also converts timestamps heuristically (handles ns/µs/s -> ms) to make plotting easier; frontend converts timestamps to seconds-since-first-sample for readable x-axis labels.

**How frontend plotting works**
- The UI uses Chart.js to render two line charts: Acceleration (x,y,z) and Gyroscope (x,y,z).
- Charts are populated with an initial batch (`/api/latest_file_points?count=20` by default) on page load.
- The UI polls `/api/latest_file_points` every 1s and appends only new messages by tracking the last returned message; charts trim older points to a reasonable max.
- Missing components are represented as gaps (Chart.js `NaN` values) instead of `null` to avoid rendering errors.

**Troubleshooting**
- Blank UI or no plotted points:
  - Confirm backend returns data: `curl http://localhost:5000/api/latest_file_points?count=20` should return JSON array with `accel` objects.
  - Confirm frontend container is running and reachable: `docker compose ps` and `docker compose logs frontend`.
  - Hard-refresh browser to ensure updated JS is loaded (Ctrl+F5 or DevTools → Empty Cache and Hard Reload).
  - If Chart.js errors about reading `x` from `null`, ensure the frontend JS version is updated; `null` gaps were replaced with `NaN` to avoid that.

- HDFS errors / files not found:
  - Confirm `/iot/sensors` exists in HDFS: `curl -i 'http://namenode:9870/webhdfs/v1/iot/sensors?op=LISTSTATUS'`.
  - If files exist in a `date=YYYY-MM-DD` subfolder, the backend now discovers `*.json` files and enumerates them.

- If timestamps look wrong:
  - Device timestamps in message examples appear to be large monotonic counters; the frontend converts those to seconds-since-first-sample for plotting. If you want absolute wall-clock times, ensure messages include epoch milliseconds or provide a mapping from device timestamp to epoch time.

**Security & production notes**
- The frontend currently runs Flask's development server in debug mode inside the `frontend` service. For production use:
  - Run via a production WSGI server (e.g., `gunicorn`) and configure a reverse proxy (nginx) to terminate TLS and serve static assets.
  - Do not run `pip install` as root in production images; build a proper Dockerfile with a virtual environment or pinned dependencies.
  - Use a secure HDFS setup and avoid `InsecureClient` in production; enable Kerberos or appropriate authentication.

**Next steps and enhancements**
- Plot magnitude (sqrt(x^2+y^2+z^2)) as an extra series or chart.
- Add controls to toggle axes, pause/resume streaming, change sampling window.
- Store parsed messages into a time-series DB (InfluxDB, Prometheus) for advanced queries and dashboards.
- Add unit tests for the parser in `scripts/frontend/app.py` to validate different incoming message formats.

**Credits & notes**
- Frontend uses `Chart.js` (CDN) for plotting.
- HDFS access uses `hdfs` Python package (WebHDFS client).
- Kafka images are Confluent CP images used for convenience in this demo.

If you want, I can also:
- Add a Dockerfile for the `frontend` service to avoid pip installing on container start.
- Add a brief `make` file or shell wrapper to start/stop the whole demo.
- Add unit-tests for message parsing and a simple CI job.

---

If you'd like, tell me what tone/length you prefer for the README (short summary, developer-focused, or tutorial-style with screenshots) and I can reformat it accordingly.
