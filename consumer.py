import json
from kafka import KafkaConsumer
import sys

# --- Configuration ---
TOPIC_NAME = "learning-topic"
KAFKA_BROKER = "localhost:9092"
CONSUMER_GROUP_ID = "my-learning-group" # A unique name for your consumer group

print("Starting Kafka Consumer...")
print(f"Connecting to broker at {KAFKA_BROKER}...")

try:
    # Initialize the consumer
    consumer = KafkaConsumer(
        TOPIC_NAME,  # The topic (or topics) to subscribe to
        bootstrap_servers=[KAFKA_BROKER],
        group_id=CONSUMER_GROUP_ID,
        
        # 'earliest' means we'll read all messages from the beginning of the topic
        # 'latest' would mean we only read new messages sent after we start
        auto_offset_reset='earliest', 
        
        # We use json.loads to deserialize the bytes back into a Python dict
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    print("Successfully connected to Kafka broker.")
    print(f"Subscribed to topic: '{TOPIC_NAME}' as group: '{CONSUMER_GROUP_ID}'")

except Exception as e:
    print(f"Error connecting to Kafka broker: {e}")
    print("Please ensure Kafka is running (e.g., via 'docker-compose up -d').")
    sys.exit(1)


# --- Message Consumption Loop ---
print("\nWaiting for messages... (Press Ctrl+C to stop)")

try:
    # The consumer object is an iterator. 
    # This 'for' loop will run forever, blocking and waiting for new messages.
    # It continuously "polls" Kafka for new records.
    for message in consumer:
        # 'message' is an object with lots of useful info
        print("-" * 20)
        print(f"Received Message:")
        print(f"  Topic:     {message.topic}")
        print(f"  Partition: {message.partition}")
        print(f"  Offset:    {message.offset}")
        # The 'value' is our deserialized JSON dictionary
        print(f"  Value:     {message.value}")
        print("-" * 20)

except KeyboardInterrupt:
    print("\nStopping consumer...")

finally:
    # --- Cleanup ---
    # Close the consumer connection
    print("Closing consumer connection.")
    consumer.close()
    print("Consumer shut down.")
