### Step 0: You MUST Re-create the Topic with Partitions

You cannot change the partition count of an existing topic easily. Your current `learning-topic` only has 1 partition. We must create a *new* topic with multiple partitions.

1.  **Stop and clean up your old containers:**

    ```bash
    docker-compose down
    ```

2.  **Start the Kafka cluster again:**

    ```bash
    docker-compose up -d
    ```

    (Wait 10-15 seconds for it to start.)

3.  **Exec into the `kafka` container** to run admin commands:

    ```bash
    docker exec -it kafka /bin/bash
    ```

4.  **Inside the container's shell,** create your new topic. Let's call it `multi-partition-topic` and give it **4 partitions**:

    ```bash
    # This is run *inside* the docker container's shell
    kafka-topics --create \
      --topic multi-partition-topic \
      --bootstrap-server localhost:29092 \
      --partitions 4 \
      --replication-factor 1
    ```

5.  Type `exit` to leave the container's shell.

Your Kafka cluster now has a topic named `multi-partition-topic` with 4 partitions (0, 1, 2, 3).

-----

### 1\. Producer Changes (`producer.py`)

Instead of *manually* calculating the hash, we'll do it the "Kafka-native" way. We will provide a `key` with our message.

Kafka's default partitioner will **automatically hash the key** and use that to decide which partition to send to. All messages with the *same key* will always go to the *same partition*.

Here are the modifications:

```python
import time
import json
from kafka import KafkaProducer
import sys
import random # <--- ADD THIS

# --- Configuration ---
TOPIC_NAME = "multi-partition-topic" # <--- CHANGE THIS
KAFKA_BROKER = "localhost:9092"
NUM_PARTITIONS = 4 # <--- ADD THIS (Must match what you created)

print("Starting Kafka Producer...")
# ... (rest of the connection logic is the same) ...

# --- ADD THIS: A callback for successful sends ---
def on_send_success(record_metadata):
    """
    Callback function to print partition info
    """
    print(f"Message Sent Successfully:")
    print(f"  Topic:     {record_metadata.topic}")
    print(f"  Partition: {record_metadata.partition}") # <--- This is the info we want
    print(f"  Offset:    {record_metadata.offset}")

# --- Message Production Loop ---
print(f"Starting to send messages to topic: '{TOPIC_NAME}'")
print("Press Ctrl+C to stop.")

message_counter = 0
try:
    while True:
        # --- MODIFY THIS BLOCK ---
        
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
        
        # --- END OF MODIFIED BLOCK ---
        
        # We removed the old synchronous print
        message_counter += 1
        time.sleep(1)

except KeyboardInterrupt:
# ... (rest of the file is the same) ...
```

**Why this is better:** By sending `key=10`, `key=20`, etc., Kafka *guarantees* that all messages for "user 10" will land on the *same partition* in the correct order. This is how Kafka maintains ordering for related messages (e.g., all events for one customer) while still scaling out writes across multiple partitions.

-----

### 2\. Consumer Changes (`consumer.py`)

This is the best part: **you barely have to change anything\!**

The `message` object your consumer receives *already contains* all the metadata, including the partition. Your original print statement was already showing it.

We just need to update the topic name and we can highlight the partition in the printout.

```python
import json
from kafka import KafkaConsumer
import sys

# --- Configuration ---
TOPIC_NAME = "multi-partition-topic" # <--- CHANGE THIS
KAFKA_BROKER = "localhost:9092"
CONSUMER_GROUP_ID = "my-learning-group" 

# ... (connection logic is the same) ...

# --- Message Consumption Loop ---
print("\nWaiting for messages... (Press Ctrl+C to stop)")

try:
    for message in consumer:
        # The 'message' object already has what we need!
        print("-" * 20)
        print(f"Received Message:")
        print(f"  Topic:     {message.topic}")
        
        # --- THIS IS WHAT YOU ASKED FOR ---
        print(f"  Partition: {message.partition}") 
        
        print(f"  Offset:    {message.offset}")
        
        # We can also see the key (as bytes)
        print(f"  Key:       {message.key.decode('utf-8')}") 
        
        print(f"  Value:     {message.value}")
        print("-" * 20)

except KeyboardInterrupt:
# ... (rest of the file is the same) ...
```

### What You Will See Now:

When you run the new producer and consumer:

1.  The **Producer (Terminal 3)** will print messages like:

    ```
    Message Sent Successfully:
      Topic:     multi-partition-topic
      Partition: 2  <-- (e.g., all "user_id: 10" messages go here)
      Offset:    45
    Message Sent Successfully:
      Topic:     multi-partition-topic
      Partition: 0  <-- (e.g., all "user_id: 20" messages go here)
      Offset:    31
    ```

2.  The **Consumer (Terminal 2)** will print the *same* information, confirming where it read from:

    ```
    --------------------
    Received Message:
      Topic:     multi-partition-topic
      Partition: 2
      Offset:    45
      Key:       10
      Value:     {'message_id': 88, 'user_id': 10, ...}
    --------------------
    --------------------
    Received Message:
      Topic:     multi-partition-topic
      Partition: 0
      Offset:    31
      Key:       20
      Value:     {'message_id': 89, 'user_id': 20, ...}
    --------------------
    ```


> "...each time once I commit the message, the offset keeps moving forward only in the partition right?"

**Yes, you are 100% correct.** The offset is not one number for the whole topic. It is a separate number *per partition, per consumer group*.

If your group `my-learning-group` reads from 4 partitions, Kafka is actually tracking 4 separate offsets for you:

  * `my-learning-group` offset for partition 0 is 102
  * `my-learning-group` offset for partition 1 is 87
  * `my-learning-group` offset for partition 2 is 115
  * `my-learning-group` offset for partition 3 is 92

-----

### 1\. How do I clear all offsets to start from 0?

Your suggestion ("restart the container & create the partition again") is the "nuke it from orbit" approach, which *would* work by deleting all the data, but it's not the easiest way.

The offset isn't stored in your consumer; it's stored by Kafka on the broker, tied to the `CONSUMER_GROUP_ID`.

So, the **easiest and cleanest way** to re-read all messages from the beginning is to:

**Change your `CONSUMER_GROUP_ID` in `consumer.py`**

```python
# In consumer.py
...
# Just change this string to something new!
CONSUMER_GROUP_ID = "my-learning-group-v2" 
...
```

**Why this works:**
When you run the consumer with this *new* group ID (`my-learning-group-v2`), Kafka says, "Ah, a brand new consumer group I've never seen before. It has no saved offsets."

Then, your consumer's setting `auto_offset_reset='earliest'` kicks in. This setting *only* applies when no offsets are found. It tells Kafka, "Since I'm new, please start me at the very beginning (offset 0) of all partitions."

You can just change the "v2" to "v3", "v4", etc., every time you want to re-process all messages from the start. This is what developers do *all the time* during testing.

-----

### 2\. Why didn't we have to create the first topic manually?

Your observation is perfect. You *didn't* create the first topic (`learning-topic`) manually.

This happened because our Kafka broker is running with a default setting called **`auto.create.topics.enable=true`**.

When this setting is `true` (which it is in the `docker-compose.yml` environment variables, or as a broker default), any producer that tries to write to a topic that *doesn't exist* will **automatically trigger Kafka to create it**.

**But (and this is the key part):** It creates that topic using the broker's default settings, which almost always means `num.partitions=1`.

So, your new understanding is exactly right:

  * **For a quick 1-partition topic:** You can be "lazy" and just let the producer auto-create it.
  * **If you need a specific partition count:** You **must** create the topic manually *beforehand* using the admin commands, just as we did. This is the only way to override the default and get your 4 partitions.