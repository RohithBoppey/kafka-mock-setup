import time
import json
from kafka import KafkaProducer
import sys
import random

# --- Configuration ---
TOPIC_NAME = "multi-partition-topic"
KAFKA_BROKER = "localhost:9092"
NUM_PARTITIONS = 4 # this number should match with the command we execute in the container 

print("Starting Kafka Producer...")
print(f"Connecting to broker at {KAFKA_BROKER}...")

# --- New callback function for successful sends ---
def on_send_success(record_metadata):
    """
    Callback function to print partition info
    """
    print(f"Message Sent Successfully:")
    print(f"  Topic:     {record_metadata.topic}")
    print(f"  Partition: {record_metadata.partition}") # <--- This is the info we want
    print(f"  Offset:    {record_metadata.offset}")


try:
    # Initialize the producer
    # We use json.dumps to serialize our Python dicts into JSON strings
    # and then encode('utf-8') to turn them into bytes, which Kafka requires.
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    print("Successfully connected to Kafka broker.")

except Exception as e:
    print(f"Error connecting to Kafka broker: {e}")
    print("Please ensure Kafka is running (e.g., via 'docker-compose up -d').")
    sys.exit(1)


# --- Message Production Loop ---
print(f"Starting to send messages to topic: '{TOPIC_NAME}'")
print("Press Ctrl+C to stop.")

message_counter = 0
try:
    while True:
        # 1. Generate a random ID (let's pick from a small set to see grouping)
        random_id = random.choice([10, 20, 30, 40, 50])
        
        # 2. Create the key. It MUST be bytes.
        #    Kafka will hash this key to pick a partition.
        key_bytes = str(random_id).encode('utf-8')

        # 3. Create the message, including the ID
        message = {
            'message_id': message_counter,
            'user_id': random_id, # We use the random ID as a "user_id"
            'content': f'This is message number {message_counter}',
            'timestamp': time.time()
        }

        # 4. Send the message with the key
        #    We also attach our callback to see the partition
        producer.send(
            TOPIC_NAME, 
            value=message, 
            key=key_bytes
        ).add_callback(on_send_success)
        
        # We removed the old synchronous print
        message_counter += 1
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping producer...")

finally:
    # --- Cleanup ---
    # Call flush() to ensure all outstanding messages are sent
    print("Flushing remaining messages...")
    producer.flush()
    # Close the producer connection
    print("Closing producer connection.")
    producer.close()
    print("Producer shut down.")
