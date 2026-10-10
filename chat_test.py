import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from agent_api.agent import chat
print(chat("t1", "How much rice stock is there and how many days will it last? Answer in Telugu."))
print("---")
print(chat("t1", "Draft supplier orders for low stock items. Answer in Telugu."))
