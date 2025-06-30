import os
import time

with open("log.txt", "w") as f:
    f.write("✅ bot.py has started!\n")
    f.flush()

i = 1
while True:
    with open("log.txt", "a") as f:
        f.write(f"Loop {i}\n")
        f.flush()
    print(f"Loop {i}")
    time.sleep(15)
    i += 1
