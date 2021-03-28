import os
import logging
from azure.logging.eventhub import EventHubHandler
from azure.eventhub import EventData, EventHubProducerClient

CNS = os.environ.get("CNS")
CAP = 500000

# cli = EventHubProducerClient.from_connection_string(CNS)
# btc = cli.create_batch()
# btc.add(EventData("Zorg2"))
# btc.add(EventData("Zorg3"))
# with cli:
#     cli.send_batch(btc)

logging.basicConfig(filename="zorg.log", filemode="w")
kh = EventHubHandler(CNS, "", capacity=5000,  flushLevel=logging.ERROR)
kh.setLevel(logging.INFO)
logger = logging.getLogger()
logging.getLogger().addHandler(kh)
logging.getLogger().setLevel(logging.INFO)
for i in range(CAP+1):
    logging.info("ZorgC%i" % i)
