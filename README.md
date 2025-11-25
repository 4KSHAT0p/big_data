Iot Sensor Data Analysis in Real Time:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
|| IoT → Kafka → HDFS → Frontend ||
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


This repository contains a small end-to-end demo that reads sensor data from an Android device, publishes it to Kafka, persists messages into HDFS, and serves a simple Flask frontend that reads stored JSON files from HDFS and visualizes accelerometer and gyroscope values using Chart.js.

Overview
--------
This project demonstrates a complete data pipeline:
1. Android IoT device publishes accelerometer/gyroscope data.
2. Kafka receives messages on the sensors topic.
3. Python consumer writes messages to HDFS in date-partitioned JSON files.
4. Flask frontend reads data from HDFS through WebHDFS and visualizes it in real time.

Architecture
------------
Android → Kafka → Python Consumer → HDFS → Flask API → Chart.js Frontend

Project Structure
-----------------
docker-compose.yml            - Full stack services
scripts/k.py                  - Kafka → HDFS consumer
scripts/frontend/app.py       - Flask backend & APIs
scripts/frontend/templates/   - HTML UI
scripts/frontend/static/      - Chart.js logic + CSS

Ports
-----
Kafka: 9092
Zookeeper: 2181
HDFS Web UI: 9870
Frontend: 5000

Quick Start
-----------
Start stack:
docker compose up -d

Check containers:
docker compose ps

Access:
Frontend → http://localhost:5000
HDFS UI → http://localhost:9870

Key API Endpoints
-----------------
GET /                                - Frontend UI
GET /api/files                       - List sensor files in HDFS
GET /api/data?count=N                - Last N messages across files
GET /api/latest_file_points?count=N  - Latest readings from newest file

Useful Commands
---------------
docker exec -it python-client bash
python scripts/frontend/app.py
curl http://localhost:5000/api/latest_file_points?count=20

HDFS Check:
curl 'http://namenode:9870/webhdfs/v1/iot/sensors?op=LISTSTATUS'

Troubleshooting
---------------
No chart data: check API response.
HDFS file not found: verify directory exists.
Timestamps off: frontend normalizes device timestamps.





