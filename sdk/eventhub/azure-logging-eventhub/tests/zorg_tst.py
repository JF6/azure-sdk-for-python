import os
import logging
from logging import Formatter
from azure.logging.eventhub import EventHubHandler #, SingleEventHubHandler
from azure.eventhub import EventData, EventHubProducerClient
import uuid
import json
import datetime
import threading
import queue
from logging.handlers import QueueHandler, QueueListener

def lg(i):
    for z in range(i):
        logging.info(f'Zirg-A-{i}-{z}-{uuid.uuid4()}')


class KustoJsonFormatter(Formatter):
    def __init__(self):
        super().__init__(None)

    def format(self, record):
        item = record.__dict__.copy()
        # item["created"] = datetime.datetime.utcfromtimestamp(item.get("created", 0)).isoformat()
        return json.dumps(item)


CNS = os.environ.get("CNS")
CAP = 50 # 500000

# cli = EventHubProducerClient.from_connection_string(CNS)
# btc = cli.create_batch()
# btc.add(EventData("Zorg2"))
# btc.add(EventData("Zorg3"))
# with cli:retry_total=10
#     cli.send_batch(btc)

logging.basicConfig(filename="zorg.log", filemode="w")
kh = EventHubHandler(CNS, capacity=400,  flushLevel=logging.ERROR, retry_total=10)
# kh = SingleEventHubHandler(CNS, retry_total=10)
fmt = KustoJsonFormatter()
kh.setFormatter(fmt)
kh.setLevel(logging.DEBUG)

# logger = logging.getLogger()
# logging.getLogger().addHandler(kh)
# logging.getLogger().setLevel(logging.DEBUG)


q = queue.Queue(-1)
qh = QueueHandler(q)
qh.setLevel(logging.DEBUG)
ql = QueueListener(q, kh)
ql.start()

root = logging.getLogger()
root.addHandler(qh)
# root.addHandler(h)
root.setLevel(logging.DEBUG)


# x=[]
# for i in range(10):
#     t=threading.Thread(target=lg, args=(CAP,))
#     x.append(t)
#     t.start()
# for i in range(CAP+1):
#     logging.debug(f"ZZorgL{i} - {uuid.uuid4()}")

# for i in x:
#     i.join()

# ql.stop()

for i in range(CAP+1):
    logging.debug(f"ZZorgL{i} - {uuid.uuid4()}")
