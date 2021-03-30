import os
import logging
from azure.logging.eventhub import EventHubHandler
from azure.eventhub import EventData, EventHubProducerClient
import uuid

CNS = os.environ.get("CNS")
CAP = 500000

# cli = EventHubProducerClient.from_connection_string(CNS)
# btc = cli.create_batch()
# btc.add(EventData("Zorg2"))
# btc.add(EventData("Zorg3"))
# with cli:
#     cli.send_batch(btc)

logging.basicConfig(filename="zorg.log", filemode="w")
kh = EventHubHandler(CNS, capacity=8192,  flushLevel=logging.ERROR)
kh.setLevel(logging.DEBUG)
logger = logging.getLogger()
logging.getLogger().addHandler(kh)
logging.getLogger().setLevel(logging.DEBUG)
for i in range(CAP+1):
    logging.debug(f"ZZorgD{i} - {uuid.uuid4()}")
