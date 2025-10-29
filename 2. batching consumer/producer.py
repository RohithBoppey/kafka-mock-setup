import time
import json
from kafka import KafkaProducer
import sys

# --- Configuration ---
TOPIC_NAME = "learning-topic"
KAFKA_BROKER = "localhost:9092"

print("Starting Kafka Producer...")
print(f"Connecting to broker at {KAFKA_BROKER}...")

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
        # Create a simple JSON message
        message = {
            'message_id': message_counter,
            'content': f'This is message number {message_counter}',
            'timestamp': time.time()
        }

        # Send the message to our topic
        producer.send(TOPIC_NAME, value=message)

        print(f"Sent: {message}")

        message_counter += 1
        
        # Wait for 1 second before sending the next message
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
