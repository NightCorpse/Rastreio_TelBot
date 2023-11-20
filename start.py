import subprocess
import platform
import time

#Continues running the bot even if it crashes
while True:
  if platform.system() == "Linux":
    process = subprocess.Popen(['python3', 'main.py'])
    process.communicate()
    time.sleep(2)
  else:
    process = subprocess.Popen(['py', 'main.py'])
    process.communicate()
    time.sleep(2)