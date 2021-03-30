"""
EventHub Logging Handler
"""
import datetime
import time
import sys
import json
import os

from azure.eventhub import EventHubProducerClient, EventData
from azure.eventhub.exceptions import EventHubError, EventDataSendError, EventDataError

def _write_batch(client, event_data_batch):
    while True:
        try:
            client.send_batch(event_data_batch)
        except Exception:  # Done on purpose : Objective is to recover whatever the exception is
            print("Err...", sys.stderr)
            time.sleep(5)
        else:
            break

connection_str = os.environ.get("CNS")
client = EventHubProducerClient.from_connection_string(connection_str, retry_total=1)
for i in range(10000):
    event_data_batch = client.create_batch()
    for j in range(1000):
        try:
            event_data_batch.add(event_data=EventData(f"Zorg-{j}-{i}"))
        except ValueError:
            _write_batch(client, event_data_batch)
            event_data_batch = client.create_batch()
            event_data_batch.add(event_data=EventData(f"Zorg-{j}-{i}"))

    if len(event_data_batch) >0:
        _write_batch(client, event_data_batch)
