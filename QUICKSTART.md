# Quick Start — IoT → Kafka → HDFS → Frontend

This one-page guide gets you from zero → UI in a few commands. It assumes Docker and Docker Compose are installed on your machine.

TL;DR
- Start everything: `docker compose up -d`
- Start frontend (if needed): `docker compose up -d frontend`
- Open UI: http://localhost:5000
- Quick API check: `curl http://localhost:5000/api/latest_file_points?count=20`

Prerequisites
- Docker (Docker Desktop on Windows)
- Docker Compose (modern `docker compose` or `docker-compose`)

Start the stack (recommended)
```pwsh
# from repo root
docker compose up -d
```

Start only frontend (faster after first run)
```pwsh
docker compose up -d frontend
```

Check running containers
```pwsh
docker compose ps
```

Tail frontend logs (helpful while debugging)
```pwsh
docker compose logs --follow --tail=200 frontend
```

Open the UI
- Visit: `http://localhost:5000`

Quick API checks
- List discovered HDFS files:
```pwsh
curl http://localhost:5000/api/files | jq '.'
```
- Get last N points from the newest file (default N=20):
```pwsh
curl http://localhost:5000/api/latest_file_points?count=20 | jq '.'
```

If you prefer to run inside the `python-client` container (dev mode)
```pwsh
docker exec -it python-client bash
pip install -r /scripts/frontend/requirements.txt
python /scripts/frontend/app.py
# then open http://localhost:5000
```

Screenshots (placeholders)
- Take a screenshot of the UI and save under `docs/screenshots/ui.png` then add it here to the docs by placing the file and using the following markdown:

```md
![Frontend UI](docs/screenshots/ui.png)
```

- Example recommended screenshots:
  - `docs/screenshots/ui.png` — main dashboard showing Accel & Gyro charts
  - `docs/screenshots/api-curl.png` — terminal output of `curl http://localhost:5000/api/latest_file_points?count=20`

Troubleshooting — quick list
- Blank UI or no points:
  - Run `curl http://localhost:5000/api/latest_file_points?count=20` — API should return a JSON array with `accel` objects.
  - Hard-refresh browser (Ctrl+F5) to pick up new frontend JS.
  - Check frontend logs: `docker compose logs --follow --tail=200 frontend`.

- HDFS file not found:
  - Inspect HDFS via WebHDFS (from within `frontend` container):
    - `docker compose exec frontend bash -lc "curl -i 'http://namenode:9870/webhdfs/v1/iot/sensors?op=LISTSTATUS'"`
    - List inside a date folder:
      - `curl -sS 'http://namenode:9870/webhdfs/v1/iot/sensors/date=YYYY-MM-DD?op=LISTSTATUS'`

- Chart.js errors (e.g., reading `.x` of null):
  - Ensure you hard-refreshed the page; the code replaces `null` with `NaN` gaps and sets `spanGaps`.

Notes & tips
- The frontend polls the newest HDFS file every second and appends new points; if your files are static you will only see the initial batch.
- Device timestamps in sample data are converted to seconds-since-first-sample in the UI for readability.

Want this as a one-click script?
- I can add a small `make` file or `scripts/start.sh` that runs the compose commands for you and prints the UI URL.

---
Keep this file minimal — use `README.md` for deep details and the architecture overview.
