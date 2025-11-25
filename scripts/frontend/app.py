from flask import Flask, jsonify, render_template, request
from hdfs import InsecureClient
import json
import time

app = Flask(__name__, template_folder='templates', static_folder='static')

# HDFS client (matches existing scripts)
client = InsecureClient('http://namenode:9870', user='root')
SENSORS_ROOT = '/iot/sensors'


def collect_file_paths():
    """Collect file paths under SENSORS_ROOT recursively (one level expected).
    Returns list of HDFS paths like '/iot/sensors/2025-11-25/msg_....json' or
    '/iot/sensors/msg_....json'."""
    paths = []
    try:
        entries = client.list(SENSORS_ROOT)
    except Exception:
        return []

    for name in entries:
        path = f"{SENSORS_ROOT}/{name}"
        # If entry looks like a JSON file (msg_* or any .json) add it
        if name.endswith('.json'):
            paths.append(path)
            continue
        # try listing subdirectory (collect any .json files inside)
        try:
            sub = client.list(path)
            for fn in sub:
                if fn.endswith('.json'):
                    paths.append(f"{path}/{fn}")
        except Exception:
            continue

    return paths


def get_mtime(path):
    try:
        st = client.status(path)
        # In some HDFS configs key could be 'modificationTime' or 'modification_time'
        return int(st.get('modificationTime') or st.get('modification_time') or 0)
    except Exception:
        # Fallback: parse timestamp from filename msg_<ms>.json
        try:
            base = path.split('/')[-1]
            ts = base.split('_')[1].split('.')[0]
            return int(ts)
        except Exception:
            return 0


def parse_sensor_message(raw):
    """Try to parse JSON and extract gyro & acceleration values.
    Returns dict: {'ts': int_ms, 'accel': {'x':..,'y':..,'z':..}, 'gyro': {...}}"""
    # Some messages come prefixed like "Buffered: {...}" or
    # "MQTT: topic {...}". Others may use Python single quotes.
    raw = raw.strip()
    # try to extract JSON object portion
    if '{' in raw and '}' in raw:
        start = raw.find('{')
        end = raw.rfind('}')
        json_text = raw[start:end+1]
        # fix single quotes -> double quotes for simple Python-dict strings
        if json_text.count("'") > 0 and json_text.count('"') == 0:
            json_text = json_text.replace("'", '"')
    else:
        json_text = raw

    try:
        obj = json.loads(json_text)
    except Exception:
        # fallback: try loading the raw string directly
        try:
            obj = json.loads(raw)
        except Exception:
            return None


    # find timestamp
    ts = None
    if isinstance(obj, dict):
        ts = obj.get('timestamp') or obj.get('ts') or obj.get('time')

    # try to infer from top-level numeric string
    if ts is None:
        # fallback to current time
        ts = int(time.time() * 1000)

    # helpers to lookup different key names
    def find_key(d, keys):
        for k in keys:
            if k in d:
                return d[k]
        return None

    accel = None
    gyro = None
    if isinstance(obj, dict):
        # common IoT shape: {'type': 'android.sensor.accelerometer', 'values': [...]}
        typ = obj.get('type', '') or ''
        vals = obj.get('values') or obj.get('value') or obj.get('accel') or obj.get('acceleration')
        if isinstance(vals, list) and len(vals) >= 3:
            if 'accelerometer' in typ or 'accel' in typ:
                accel = vals
            if 'gyro' in typ or 'gyroscope' in typ or 'rotation' in typ:
                gyro = vals
        # fallback lookups
        accel = accel or find_key(obj, ['accel', 'acceleration', 'accelerometer'])
        gyro = gyro or find_key(obj, ['gyro', 'gyroscope', 'rotationRate'])

    # Normalize shapes: if provided as list [x,y,z] convert to dict
    def normalize_vec(v):
        if v is None:
            return None
        if isinstance(v, list) and len(v) >= 3:
            return {'x': float(v[0]), 'y': float(v[1]), 'z': float(v[2])}
        if isinstance(v, dict):
            # try keys x,y,z or 0,1,2
            if 'x' in v or 'y' in v or 'z' in v:
                return {k: float(v.get(k, 0.0)) for k in ['x', 'y', 'z']}
            # try other names
            for a in ['ax', 'ay', 'az']:
                if a in v:
                    return {'x': float(v.get('ax', 0.0)), 'y': float(v.get('ay', 0.0)), 'z': float(v.get('az', 0.0))}
        # fallback try numeric value
        try:
            return {'x': float(v), 'y': 0.0, 'z': 0.0}
        except Exception:
            return None

    accel_n = normalize_vec(accel)
    gyro_n = normalize_vec(gyro)

    # ensure timestamp is milliseconds int
    try:
        ts = int(float(ts))
        # Heuristics: convert ns/us/s -> ms
        if ts > 1e14:
            # likely nanoseconds -> ms
            ts = int(ts / 1e6)
        elif ts > 1e12:
            # likely microseconds -> ms
            ts = int(ts / 1e3)
        elif ts < 1e12:
            # probably seconds -> ms
            if ts < 1e11:
                ts = int(ts * 1000)
            # else assume already ms
    except Exception:
        ts = int(time.time() * 1000)

    return {'ts': ts, 'accel': accel_n, 'gyro': gyro_n}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/files')
def api_files():
    paths = collect_file_paths()
    files = [{'path': p, 'mtime': get_mtime(p)} for p in paths]
    files.sort(key=lambda x: x['mtime'], reverse=True)
    return jsonify(files)


@app.route('/api/data')
def api_data():
    # ?count=100 -> last N messages
    count = int(request.args.get('count', 200))
    paths = collect_file_paths()
    items = []
    for p in paths:
        items.append((p, get_mtime(p)))
    items.sort(key=lambda x: x[1], reverse=True)

    results = []
    read_count = 0

    for p, _ in items:
        if read_count >= count:
            break
        try:
            with client.read(p, encoding='utf-8') as fh:
                raw = fh.read()
        except Exception:
            continue

        if not raw:
            continue

        # If file is a JSON array -> parse elements
        trimmed = raw.strip()
        try:
            if trimmed.startswith('['):
                arr = json.loads(trimmed)
                for elem in arr:
                    if read_count >= count:
                        break
                    # elem may already be a dict or a JSON string
                    if isinstance(elem, dict):
                        raw_line = json.dumps(elem)
                    else:
                        raw_line = str(elem)
                    parsed = parse_sensor_message(raw_line)
                    if parsed:
                        results.append(parsed)
                        read_count += 1
                if read_count >= count:
                    break
                continue
        except Exception:
            # fall through to NDJSON / line parsing
            pass

        # Treat file as newline-delimited messages (NDJSON) or prefixed lines
        for line in raw.splitlines():
            if read_count >= count:
                break
            line = line.strip()
            if not line:
                continue
            parsed = parse_sensor_message(line)
            if parsed:
                results.append(parsed)
                read_count += 1

    # return in chronological order (old->new)
    results = list(reversed(results))
    return jsonify(results)


def latest_file_path():
    paths = collect_file_paths()
    if not paths:
        return None
    items = [(p, get_mtime(p)) for p in paths]
    items.sort(key=lambda x: x[1], reverse=True)
    return items[0][0]


@app.route('/api/latest_file_points')
def api_latest_file_points():
    # Returns the last N messages from the most recent file only
    count = int(request.args.get('count', 200))
    path = latest_file_path()
    if not path:
        return jsonify([])

    try:
        with client.read(path, encoding='utf-8') as fh:
            raw = fh.read()
    except Exception:
        return jsonify([])

    messages = []
    trimmed = raw.strip()
    try:
        if trimmed.startswith('['):
            arr = json.loads(trimmed)
            for elem in arr:
                if isinstance(elem, dict):
                    parsed = parse_sensor_message(json.dumps(elem))
                else:
                    parsed = parse_sensor_message(str(elem))
                if parsed:
                    messages.append(parsed)
        else:
            for line in raw.splitlines():
                if not line.strip():
                    continue
                parsed = parse_sensor_message(line)
                if parsed:
                    messages.append(parsed)
    except Exception:
        pass

    # return only the last `count` entries in chronological order
    messages = messages[-count:]
    return jsonify(messages)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
