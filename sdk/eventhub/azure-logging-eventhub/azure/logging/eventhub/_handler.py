"""
EventHub Logging Handler
"""
import logging
import logging.handlers
import datetime
import time
import sys
import json

from azure.eventhub import EventHubProducerClient, EventData
from azure.eventhub.exceptions import EventHubError, EventDataSendError, EventDataError

class EventHubHandler(logging.handlers.MemoryHandler):
    """A handler class which writes un-formatted logging records to an Eventhub (in order to ingest to Ksuto)."""

    def close(self):
        """Cleanup Eventhub client
        """
        super().close()
        self.client.close()

    def __init__(self, connection_str: str, capacity=8192, flushLevel=logging.ERROR, retries=[5, 30, 60]) -> None:
        """Constructor

        Args:
            connection_str: eventHub connection string
            capacity (int, optional): Number of records before flushing. Defaults to 8192.
            flushLevel (int, optional): Miminal level to trigger the flush, even if the buffer is not full. Defaults to logging.ERROR.
            retries (list, optional): delay between retries for ingestion error. Defaults to [5s, 30s, 60s]. Can be [] if no retry.
        """
        super().__init__(capacity, flushLevel=flushLevel)

        logging.getLogger("uamqp").propagate = False   # In order to avoid recursive calls in case of DEBUG level.

        self.client = EventHubProducerClient.from_connection_string(connection_str, retry_total=10)

        self.first_record = None
        self.retries = retries

    def emit(self, record):
        """
        Emit a record.
        Just add the record in the records list
        """

        if not self.buffer:
            self.first_record = record  # in case of error in flush, dump the ff"Zorg-{j}-{i}")irst record.
        super().emit(record)

    def _write_batches(self, event_data_batch_list):
        # retries = self.retries.copy()

        # retries.append(0)  # in order to ensure a try (or the last retry to go on)
        # while retries:
        for event_data_batch in event_data_batch_list:
            try:
                self.client.send_batch(event_data_batch)
            except Exception as ex:  # Done on purpose : Objective is to recover whatever the exception is
                # waiting_time = retries.pop(0)
                # if retries:
                #     print("Exception, retrying in {} seconds".format(waiting_time), file=sys.stderr)
                #     time.sleep(waiting_time)
                # else:
                self.handleError(self.first_record)
            # else:
            #     break

    def flush(self):
        """
        Flush the records in Kusto
        """

        event_data_batch_list = []
        event_data_batch = self.client.create_batch()

        if self.buffer:
            self.acquire()
            # log_dict = [x.__dict__ for x in self.buffer].copy()
            # convert to iso datetime as Kusto truncates the milliseconds if a float is provided.
            # for item in log_dict:
            for item in self.buffer:
                # item["created"] = datetime.datetime.utcfromtimestamp(item.get("created", 0)).isoformat()
                try:
                    event_data_batch.add(event_data=EventData(json.dumps(item.__dict__)))
                except ValueError:
                    event_data_batch_list.append(event_data_batch)
                    event_data_batch = self.client.create_batch()
                    event_data_batch.add(event_data=EventData(json.dumps(item.__dict__)))

            if len(event_data_batch)>0:
                event_data_batch_list.append(event_data_batch)
                
            if event_data_batch_list:
                self._write_batches(event_data_batch_list)

            self.first_record = None
            self.buffer.clear()
            event_data_batch_list.clear()
            # self.event_data_batch = None
            # self.event_data_batch = self.client.create_batch()
            self.release()
