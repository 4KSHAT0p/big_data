from hdfs import InsecureClient
from confluent_kafka import Consumer
import json, time
from datetime import datetime

client = InsecureClient('http://namenode:9870', user='root')

consumer_conf = {
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'hdfs-writer-v6',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(consumer_conf)
consumer.subscribe(['sensors'])

print("Kafka → HDFS Writer Running...")

buffer = []
last_write = time.time()

BASE_DIR = "/iot/sensors"

while True:
    msg = consumer.poll(1.0)

    # Collect messages
    if msg and not msg.error():
        data = json.loads(msg.value().decode())
        buffer.append(data)
        print("Buffered:", data)

    # Write every 5 seconds
    if time.time() - last_write >= 5 and buffer:

        # Compute daily partition
        today = datetime.now().strftime("%Y-%m-%d")
        partition_dir = f"{BASE_DIR}/date={today}"
        hdfs_file = f"{partition_dir}/data.json"

        # Ensure daily directory exists
        client.makedirs(partition_dir)

        # Try reading existing file
        try:
            with client.read(hdfs_file) as reader:
                existing = json.load(reader)
        except:
            existing = []

        # Append new data
        existing.extend(buffer)

        # Write full day's data
        client.write(hdfs_file, json.dumps(existing, indent=2), overwrite=True)

        print(f"Written {len(buffer)} messages → {hdfs_file}")

        buffer = []
        last_write = time.time()
