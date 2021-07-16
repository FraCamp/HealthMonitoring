import os

import docker
import random
import time
import subprocess
from subprocess import PIPE

loss = "25%"
monitoring_period = 2
client = docker.from_env()
safe_containers = ["/antagonist", "/agent"]


def stop_random_container():
    containers = client.containers.list()
    filtered_containers = list(filter(filter_containers, containers))
    if len(filtered_containers) > 0:
        num = random.randint(0, len(filtered_containers) - 1)
        filtered_containers[num].stop()
        print(filtered_containers[num].attrs.get("Name") + " has been stopped.")
    else:
        print("No more containers left!")


def change_loss():
    num = random.randint(10, 80)
    loss = str(num) + "%"
    print("Packet loss changed to " + loss)
    os.system("tc qdisc del dev eth0 root")
    os.system("tc qdisc add dev eth0 root netem loss " + loss)


def filter_containers(container):
    if container.attrs.get("Name") in safe_containers:
        return False
    return True


while True:
    try:
        if random.randint(0, 10) > 8:
            stop_random_container()
        if random.randint(0, 10) > 7:
            change_loss()
        time.sleep(monitoring_period)
    except Exception as e:
        print(repr(e))
        time.sleep(monitoring_period)
        continue
