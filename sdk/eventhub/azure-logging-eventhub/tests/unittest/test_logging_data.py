import platform
import os
import pytest
import uamqp
import logging
from packaging import version
from azure.eventhub import _common

from mock import patch

pytestmark = pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="This is ignored for PyPy")


from azure.eventhub import EventData, EventDataBatch
from azure.logging.eventhub import EventHubHandler  #, SingleEventHubHandler


def mocked_client(*args, **kwargs):
    class MockDataBatch:
        def add(self, *args, **kwargs):
            pass
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



def test_body_json():
    event_data = EventData('{"a":"b"}')
    assert str(event_data) == "{ body: '{\"a\":\"b\"}', properties: {} }"
    assert repr(event_data) == "EventData(body='{\"a\":\"b\"}', properties={}, offset=None, sequence_number=None, partition_key=None, enqueued_time=None)"
    jo = event_data.body_as_json()
    assert jo["a"] == "b"


def test_body_wrong_json():
    event_data = EventData('aaa')
    with pytest.raises(TypeError):
        event_data.body_as_json()


def test_app_properties():
    app_props = {"a": "b"}
    event_data = EventData("")
    event_data.properties = app_props
    assert str(event_data) == "{ body: '', properties: {'a': 'b'} }"
    assert repr(event_data) == "EventData(body='', properties={'a': 'b'}, offset=None, sequence_number=None, partition_key=None, enqueued_time=None)"
    assert event_data.properties["a"] == "b"


def test_sys_properties():
    properties = uamqp.message.MessageProperties()
    properties.message_id = "message_id"
    properties.user_id = "user_id"
    properties.to = "to"
    properties.subject = "subject"
    properties.reply_to = "reply_to"
    properties.correlation_id = "correlation_id"
    properties.content_type = "content_type"
    properties.content_encoding = "content_encoding"
    properties.absolute_expiry_time = 1
    properties.creation_time = 1
    properties.group_id = "group_id"
    properties.group_sequence = 1
    properties.reply_to_group_id = "reply_to_group_id"
    message = uamqp.Message(properties=properties)
    message.annotations = {_common.PROP_OFFSET: "@latest"}
    ed = EventData._from_message(message)  # type: EventData

    assert ed.system_properties[_common.PROP_OFFSET] == "@latest"
    assert ed.system_properties[_common.PROP_CORRELATION_ID] == properties.correlation_id
    assert ed.system_properties[_common.PROP_MESSAGE_ID] == properties.message_id
    assert ed.system_properties[_common.PROP_CONTENT_ENCODING] == properties.content_encoding
    assert ed.system_properties[_common.PROP_CONTENT_TYPE] == properties.content_type
    assert ed.system_properties[_common.PROP_USER_ID] == properties.user_id
    assert ed.system_properties[_common.PROP_TO] == properties.to
    assert ed.system_properties[_common.PROP_SUBJECT] == properties.subject
    assert ed.system_properties[_common.PROP_REPLY_TO] == properties.reply_to
    assert ed.system_properties[_common.PROP_ABSOLUTE_EXPIRY_TIME] == properties.absolute_expiry_time
    assert ed.system_properties[_common.PROP_CREATION_TIME] == properties.creation_time
    assert ed.system_properties[_common.PROP_GROUP_ID] == properties.group_id
    assert ed.system_properties[_common.PROP_GROUP_SEQUENCE] == properties.group_sequence
    assert ed.system_properties[_common.PROP_REPLY_TO_GROUP_ID] == properties.reply_to_group_id


def test_event_data_batch():
    batch = EventDataBatch(max_size_in_bytes=100, partition_key="par")
    batch.add(EventData("A"))
    assert str(batch) == "EventDataBatch(max_size_in_bytes=100, partition_id=None, partition_key='par', event_count=1)"
    assert repr(batch) == "EventDataBatch(max_size_in_bytes=100, partition_id=None, partition_key='par', event_count=1)"

    # In uamqp v1.2.8, the encoding size of a message has changed. delivery_count in message header is now set to 0
    # instead of None according to the C spec.
    # This uamqp change is transparent to EH users so it's not considered as a breaking change. However, it's breaking
    # the unit test here. The solution is to add backward compatibility in test.
    if version.parse(uamqp.__version__) >= version.parse("1.2.8"):
        assert batch.size_in_bytes == 97 and len(batch) == 1
    else:
        assert batch.size_in_bytes == 89 and len(batch) == 1
    with pytest.raises(ValueError):
        batch.add(EventData("A"))
