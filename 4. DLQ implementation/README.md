- DLQ sits in the consumer part now, as if the message is invalid, push it to DLQ
- DLQ is just another Kafka topic where you send messages that your consumer *failed* to process for some reason (bad JSON, failed business logic, etc.).
- This unblocks your main processing pipeline. Instead of your consumer crashing or getting "stuck" on a "poison pill" message, it just calmly moves the bad message to the DLQ and keeps going.

### How to View This List of Failed Messages?

This is the best part\! Since the DLQ is "just another topic," you can view its contents using the exact same tools you already know. The simplest way is to use the built-in command-line consumer *inside* your `kafka` container.

**Open a new terminal (e.g., Terminal 5) and run this:**

1.  `docker exec -it kafka /bin/bash`

2.  Inside the container, run this command. It will subscribe to your *new* DLQ topic and print any messages that land there:

    ```bash
    # This is run *inside* the docker container's shell
    kafka-console-consumer --topic <topic_name> \
      --bootstrap-server localhost:29092 \
      --from-beginning
    ```

Leave this terminal open. When your producer sends a bad message and your consumer sends it to the DLQ, you will see the bad message appear here *instantly*. This is how you debug later—you have a perfect record of every message that failed.

-----


### What You Will See Now:

1.  **Producer (Terminal 3):** Every 5 seconds, it will print `*** Sending POISON PILL ***`.
2.  **Consumer (Terminal 2):** It will print `SUCCESSFULLY PROCESSED` 4 times, and then it will print a big `!!! FAILED TO PROCESS MESSAGE !!!` block. But most importantly... **it will not crash**. It will just keep running and process the next *good* message.
3.  **DLQ Viewer (Terminal 5):** The instant the consumer fails, you will see the raw, bad message (`this is not valid json, just a string`) appear in this terminal.

You have successfully unblocked your pipeline and safely quarantined the bad message for debugging\!