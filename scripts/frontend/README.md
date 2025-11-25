# IoT Frontend (Gyro & Acceleration)

This folder contains a simple Flask backend and a static frontend that reads JSON messages from HDFS and visualizes Gyroscope and Acceleration values.

Quick start (inside your running `python-client` container):

1. Install dependencies:

```bash
pip install -r /scripts/frontend/requirements.txt
```

2. Run the app (binds to port 5000):

```bash
python /scripts/frontend/app.py
```

3. Open the UI in your browser (from host):

http://localhost:5000

Notes:
- The app connects to HDFS Web UI at `http://namenode:9870` (matches your compose). Run it in the `bigdata` network (for example inside the `python-client` container).
- It tries to locate files under `/iot/sensors` and subfolders. It expects messages to contain either `accel`/`acceleration` and `gyro`/`gyroscope` fields (various shapes handled).
