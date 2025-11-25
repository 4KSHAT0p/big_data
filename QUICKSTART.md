Quick Start — IoT → Kafka → HDFS → Frontend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A minimal one-page guide to launch the full pipeline and reach the UI quickly.

TL;DR
-----
- Start everything: docker compose up -d
- Start only the frontend: docker compose up -d frontend
- UI: http://localhost:5000
- API test: curl http://localhost:5000/api/latest_file_points?count=20

Prerequisites
-------------
- Docker / Docker Desktop
- Docker Compose

Start the Stack
---------------
docker compose up -d

Start Only the Frontend
-----------------------
docker compose up -d frontend

Check Running Containers
------------------------
docker ps

View Frontend Logs
------------------
docker compose logs --follow --tail=200 frontend

Open the UI
-----------
http://localhost:5000

API Quick Checks
----------------
List sensor files:
curl http://localhost:5000/api/files | jq '.'

Last N data points:
curl http://localhost:5000/api/latest_file_points?count=20 | jq '.'

Developer Mode (inside python-client)
-------------------------------------
docker exec -it python-client bash
pip install -r /scripts/frontend/requirements.txt
python /scripts/frontend/app.py

Troubleshooting
---------------
Blank UI / No Data:
- curl http://localhost:5000/api/latest_file_points?count=20
- Hard-refresh browser
- docker compose logs --follow --tail=200 frontend

HDFS File Not Found:
- docker compose exec frontend bash -lc "curl -i 'http://namenode:9870/webhdfs/v1/iot/sensors?op=LISTSTATUS'"
- curl "http://namenode:9870/webhdfs/v1/iot/sensors/date=YYYY-MM-DD?op=LISTSTATUS"

Chart.js Errors:
- Hard-refresh the UI

Notes
-----
- Frontend polls newest HDFS file every second.
- Timestamps are converted to seconds-since-first-sample.
