import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from agent_api.agent import chat

print(chat("t1", "Draft supplier orders for low stock items. Answer in Telugu."))
print("---")
print(chat("t1", "Yes, approve all the draft orders. Answer in Telugu."))