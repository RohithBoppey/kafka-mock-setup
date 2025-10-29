import time
import json
from kafka import KafkaConsumer
import sys

# --- Configuration ---
TOPIC_NAME = "multi-partition-topic"
KAFKA_BROKER = "localhost:9092"
CONSUMER_GROUP_ID = "my-learning-group-2" # A new group ID for this consumer

# --- Batching Settings ---
TARGET_BATCH_SIZE = 10
TARGET_BATCH_TIMEOUT_S = 20 # 30 seconds

print("Starting Kafka Batch Consumer...")

try:
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=[KAFKA_BROKER],
        group_id=CONSUMER_GROUP_ID,
        auto_offset_reset='earliest',  # read from earliest message in the topic (other options are latest)
        
        # --- CRITICAL for manual batching ---
        # We turn OFF auto commit. We will commit offsets manually.
        enable_auto_commit=False, 
        
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    print("Successfully connected to Kafka broker.")
    
except Exception as e:
    print(f"Error connecting to Kafka broker: {e}")
    sys.exit(1)

def process_batch(batch):
    """
    This is where your logic for processing the batch of messages goes.
    """
    print(f"\n--- Processing Batch of {len(batch)} messages ---")
    for i, message in enumerate(batch):
        print(f"  {i+1}) Partition: {message.partition} |        Offset: {message.offset}")
        # Simulating a long-running task for one message
        if i == len(batch) - 1 and len(batch) > 2:
             print("  ...simulating 3-second processing task on last message...")
             time.sleep(3)
    print(f"--- Finished processing batch ---")

# --- Main Batching Loop ---
try:
    message_batch = []
    last_batch_time = time.time()

    while True:
        # 1. Poll for new messages
        # We use a short poll timeout (1000ms) to regularly check our batch conditions
        # This returns a dictionary: {TopicPartition: [list of messages]}
        poll_result = consumer.poll(timeout_ms=3000) # poll for a new batch every 3 seconds

        # 2. Add new messages to our batch
        if poll_result:
            for topic_partition, messages in poll_result.items():
                message_batch.extend(messages)
                print(f"Polled {len(messages)} messages. Current batch size: {len(message_batch)}")
        
        # 3. Check batch conditions
        time_since_last_batch = time.time() - last_batch_time
        
        batch_ready_by_size = (len(message_batch) >= TARGET_BATCH_SIZE)
        batch_ready_by_time = (time_since_last_batch >= TARGET_BATCH_TIMEOUT_S and len(message_batch) > 0)

        # 4. If a condition is met, process the batch
        if batch_ready_by_size or batch_ready_by_time:
            
            process_batch(message_batch)
            
            # 5. Manually commit the offsets
            # This tells Kafka we have successfully processed all messages in this batch.
            # If the script crashes during process_batch(), this commit won't happen,
            # and we will re-process these messages on restart.
            consumer.commit() 
            print(f"Committed offsets for {len(message_batch)} messages.")
            
            # Reset for the next batch
            message_batch = []
            last_batch_time = time.time()
        
        elif not poll_result:
            print(f"Waiting... (Batch: {len(message_batch)}/{TARGET_BATCH_SIZE}, Time: {time_since_last_batch:.0f}s/{TARGET_BATCH_TIMEOUT_S}s)")

except KeyboardInterrupt:
    print("\nStopping consumer...")
finally:
    # Always close the consumer
    consumer.close()
    print("Consumer shut down.")
