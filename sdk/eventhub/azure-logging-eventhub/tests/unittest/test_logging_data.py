import platform
import os
import pytest
import uamqp
import logging
import json
import threading
from packaging import version
from azure.eventhub import _common

from mock import patch

pytestmark = pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="This is ignored for PyPy")


from azure.eventhub import EventData, EventDataBatch
from azure.logging.eventhub import EventHubHandler  #, SingleEventHubHandler

class KustoJsonFormatter(logging.Formatter):
    def format(self, record):
        item = record.message.upper()
        return item

formatted_msg = ""

def mocked_client(*args, **kwargs):
    class MockDataBatch:
        def add(self, *args, **kwargs):
            global formatted_msg
            formatted_msg = kwargs['event_data'].body_as_str()
            
        def __len__(self):
            return 0

    class MockResponse:
        """Mock class for EventHub."""
        def __init__(self):
            self.headers = None

        def create_batch(self):
            """Get json data from response."""
            return MockDataBatch()

        def close(self):
            pass

    return MockResponse()



@patch("azure.eventhub.EventHubProducerClient.from_connection_string", side_effect=mocked_client)
@pytest.mark.parametrize("test_level",
                         ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"])
def test_basic_logging(mock_execute, test_level):
    logging.basicConfig()
    log_fn = getattr(logging, test_level.lower())
    log_msg = f"tst - {test_level}"
    # CNS = os.environ.get("CNS")
    kh = EventHubHandler("CNS", capacity=400, 
     flushLevel=logging.CRITICAL+1,  # In order to ensuure buffer is not flushed
     retry_total=10)
    kh.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(kh)

    root.setLevel(logging.DEBUG)
    log_fn(log_msg)
    assert(len(kh.buffer)==1)
    assert(kh.buffer[0].levelname == test_level)
    assert(kh.buffer[0].msg == log_msg)

@patch("azure.eventhub.EventHubProducerClient.from_connection_string", side_effect=mocked_client)
@pytest.mark.parametrize("test_level",
                         ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"])
def test_logging_flush(mock_execute, test_level):
    log_fn = getattr(logging, test_level.lower())
    log_level = getattr(logging, test_level)
    logging.basicConfig()
    # CNS = os.environ.get("CNS")
    kh = EventHubHandler("CNS", capacity=400, 
     flushLevel=log_level)

    kh.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(kh)
    root.setLevel(logging.DEBUG)
    log_fn(f"tst - {test_level}")
    assert(len(kh.buffer)==0)


@patch("azure.eventhub.EventHubProducerClient.from_connection_string", side_effect=mocked_client)
@pytest.mark.parametrize("test_message",
                         ["message1", "Message2", "Message3"])
def test_custom_format_logging(mock_execute, test_message):
    global formatted_msg

    logging.basicConfig()
    kh = EventHubHandler("CNS", capacity=400, 
     flushLevel=logging.INFO,  # In order to ensuure buffer is not flushed
     retry_total=10)
    fmt = KustoJsonFormatter()
    kh.setFormatter(fmt)
    kh.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(kh)

    root.setLevel(logging.DEBUG)
    logging.info(test_message)
    assert(formatted_msg == test_message.upper())



@patch("azure.eventhub.EventHubProducerClient.from_connection_string", side_effect=mocked_client)
def test_mt_logging(mock_execute):
    def log_it(nb_of_messages):
        for i in range(nb_of_messages):
            print(f'{i}')
            logging.info("log it")

    logging.basicConfig()
    kh = EventHubHandler("CNS", capacity=4000, 
     flushLevel=logging.CRITICAL+1,  # In order to ensuure buffer is not flushed
     retry_total=10)
    kh.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(kh)

    thread_list = []
    for thr in range(20):
        t = threading.Thread(target=log_it, args=(10,))
        t.start()
        thread_list.append(t)
    for i in thread_list:
        i.join()
    assert(len(kh.buffer)==200)
