import json
import paho.mqtt.client as mqtt
from confluent_kafka import Producer

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "android/sensor/#"

# IMPORTANT: use Docker Kafka hostname!
KAFKA_BROKER = "kafka:9092"
KAFKA_TOPIC = "sensors"

producer = Producer({'bootstrap.servers': KAFKA_BROKER})

def delivery_report(err, msg):
    if err is not None:
        print("❌ Delivery failed:", err)
    else:
        print(f"✔ Delivered to Kafka topic: {msg.topic()}")

def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected with result code:", reason_code)
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print("MQTT:", msg.topic, payload)

    producer.produce(
        KAFKA_TOPIC,
        value=payload.encode(),
        callback=delivery_report
    )
    producer.poll(0)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
