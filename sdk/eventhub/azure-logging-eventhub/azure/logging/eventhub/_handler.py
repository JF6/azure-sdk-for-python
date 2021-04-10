"""
EventHub Logging Handler
"""
import logging
import logging.handlers
from azure.eventhub import EventHubProducerClient, EventData


class EventHubHandler(logging.handlers.MemoryHandler):
    """A handler class which writes un-formatted logging records to an Eventhub."""

    def close(self):
        """Cleanup Eventhub client"""
        super().close()
        self.client.close()

    def __init__(
        self, connection_str: str, capacity=8192, flushLevel=logging.ERROR, **kwargs
    ) -> None:
        """Constructor

        Args:
            connection_str: eventHub connection string
            capacity (int, optional): Number of records before flushing.
                Defaults to 8192.
            flushLevel (int, optional): Miminal level to trigger the flush, even if the buffer is not full.
                Defaults to logging.ERROR.
        """

        super().__init__(capacity, flushLevel=flushLevel)

        logging.getLogger(
            "uamqp"
        ).propagate = False  # In order to avoid recursive calls in case of DEBUG level.

        self.client = EventHubProducerClient.from_connection_string(
            connection_str, **kwargs
        )

        self.first_record = None

    def emit(self, record):
        """
        Emit a record.
        Just add the record in the records list
        """

        if not self.buffer:
            self.first_record = (
                record  # in case of error in flush, dump the first record.
            )
        super().emit(record)

    def _write_batches(self, event_data_batch_list):
        """Output list of batches

        Args:
            event_data_batch_list ([event_data_batch]): List of data batches
        """
        for event_data_batch in event_data_batch_list:
            try:
                self.client.send_batch(event_data_batch)
            except Exception:  # pylint: disable=broad-except # Done on purpose : Objective is to recover whatever the exception is
                self.handleError(self.first_record)

    def flush(self):
        """
        Flush the records in the event hub
        """

        event_data_batch_list = []
        event_data_batch = self.client.create_batch()

        if self.buffer:
            self.acquire()
            for item in self.buffer:
                formatted_event = self.format(item)
                try:
                    event_data_batch.add(event_data=EventData(formatted_event))
                except ValueError:
                    event_data_batch_list.append(event_data_batch)
                    event_data_batch = self.client.create_batch()
                    event_data_batch.add(event_data=EventData(formatted_event))

            if len(event_data_batch) > 0:
                event_data_batch_list.append(event_data_batch)

            if event_data_batch_list:
                self._write_batches(event_data_batch_list)

            self.first_record = None
            self.buffer.clear()
            event_data_batch_list.clear()
            self.release()
