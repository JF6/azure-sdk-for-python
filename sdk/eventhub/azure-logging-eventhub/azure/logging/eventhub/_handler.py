"""
EventHub Logging Handler
"""
import logging
import logging.handlers
import datetime
import time
import sys
import json
import atexit

from azure.eventhub import EventHubProducerClient, EventData
from azure.eventhub.exceptions import EventHubError, EventDataSendError, EventDataError


class EventHubHandler(logging.handlers.MemoryHandler):
    """A handler class which writes un-formatted logging records to Kusto."""

    def close(self):
        """Cleanup Eventhub client
        """
        super().close()
        self.event_data_batch = None
        self.client.close()

    def __init__(self, connection_str, eventhub_name, capacity=5, flushLevel=logging.ERROR, retries=[5, 30, 60]):
        """Constructor

        Args:
            kcsb (KustoConnectionStringBuilder): kusto connection string
            database (string): database name
            table (string): table name
            data_format (Dataformat, optional): Format for ingestion. Defaults to DataFormat.CSV.
            useStreaming (bool, optional): Use kusto streaming endpoint. Defaults to False.
            capacity (int, optional): Number of records before flushing. Defaults to 8192.
            flushLevel (int, optional): Miminal level to trigger the flush, even if the buffer is not full. Defaults to logging.ERROR.
            retries (list, optional): retries for ingestion error. Defaults to [5s, 30s, 60s]
        """
        super().__init__(capacity, flushLevel=flushLevel)


        # in order to avoid recursive calls if level is DEBUG
        logging.getLogger("azure").propagate = False
        logging.getLogger("adal-python").propagate = False
        logging.getLogger("requests").propagate = False
        logging.getLogger("urllib3").propagate = False
        logging.getLogger("uamqp").propagate = False
        logging.getLogger("sys").propagate = False

        self.client = EventHubProducerClient.from_connection_string(connection_str)
        self.event_data_batch = self.client.create_batch()

        self.first_record = None
        self.retries = retries
        # atexit.register(self.cleanup)


    def emit(self, record):
        """
        Emit a record.
        Just add the record in the records list
        """

        if not self.buffer:
            self.first_record = record  # in case of error in flush, dump the first record.

        super().emit(record)

    def flush(self):
        """
        Flush the records in Kusto
        """
        if self.buffer:
            self.acquire()
            log_dict = [x.__dict__ for x in self.buffer].copy()
            # convert to iso datetime as Kusto truncate the milliseconds if a float is provided.
            for item in log_dict:
                item["created"] = datetime.datetime.utcfromtimestamp(item.get("created", 0)).isoformat()
                try:
                    self.event_data_batch.add(event_data=EventData(json.dumps(item)))
                except ValueError:
                    pass

            retries = self.retries.copy()
            retries.append(0)  # in order to ensure a try (or the last retry to go on)
            while retries:
                try:
                    self.client.send_batch(self.event_data_batch)
                except Exception:  # Done on purpose : Objective is to recover whatever the exception is
                    waiting_time = retries.pop(0)
                    if retries:
                        print("Exception, retrying in {} seconds".format(waiting_time), file=sys.stderr)
                        time.sleep(waiting_time)
                    else:
                        logging.Handler.handleError(self, self.first_record)
                else:
                    break
            self.first_record = None
            self.buffer.clear()
            self.event_data_batch = None
            self.event_data_batch = self.client.create_batch()
            self.release()
