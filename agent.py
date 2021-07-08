import docker
from pythonping import ping
import threading
import time

client = docker.from_env()
list = client.containers.list(all=True)
threshold = 60.0
period = 2
monitored = ["elated_mcnulty", "dazzling_spence"]

def monitor():
    for name in monitored:
        # print(cont)
        cont = client.containers.get(name)
        if cont is None:
            continue
        cont.reload()
        p_address = cont.attrs['NetworkSettings']['IPAddress']
        running = cont.attrs.get("State").get("Running")
        print("Name: " + name + "; Running: " + str(running)+ ".")
        if running:
            # print(ping_ip(p_address, 3))
            pres = ping('127.0.0.1', verbose=False, count=3)
            ploss = pres.packet_loss
            if not pres.success():
                print("Ping failed!")
                print("Restarting container.")
                cont.restart()
            elif ploss > threshold:
                print("Packet Loss: " + str(ploss) + ".")
                cont.restart()
            else:
                print("Healthy container!")
                print("Packet Loss: " + str(ploss) + " %")
        else:
            print(cont.attrs.get("Name") + " is down!")
            cont.restart()

while True:
    try:
        monitor()
        time.sleep(period)
    except:
        continue

if __name__ == '__main__':
    client = docker.from_env()
    print(client.containers.list())