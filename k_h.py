from hdfs import InsecureClient
from confluent_kafka import Consumer
import json

# HDFS client
client = InsecureClient('http://localhost:9870', user='root')

# Kafka consumer config
consumer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'hdfs-writer',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(consumer_conf)
consumer.subscribe(['sensors'])

print("Kafka → HDFS Writer Running...")

while True:
    msg = consumer.poll(1.0)

    if msg is None:
        continue

    if msg.error():
        print("Error:", msg.error())
        continue

    data = msg.value().decode()

    # Append each message to HDFS file
    client.write('/iot/sensors/data.json', data + "\n", append=True)

    print("Written to HDFS:", data)
