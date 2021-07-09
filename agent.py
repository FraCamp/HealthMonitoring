import json
import socket
import docker
import pika as pika
from pythonping import ping
import threading
import time

client = docker.from_env()
list = client.containers.list(all=True)
threshold = 60.0
ping_retries = 3
monitoring_period = 2
container_status_data = {}  # list of monitored containers
general_topics_list = [
    "set_threshold",
    "set_ping_retries",
    "set_monitoring_period",
    "status"
]
personal_topics_list = [
    "add_container",
    "remove_container",
]


def monitor():
    for name in container_status_data.keys():
        cont = client.containers.get(name)
        if cont is None:
            continue
        cont.reload()
        p_address = cont.attrs['NetworkSettings']['IPAddress']
        running = cont.attrs.get("State").get("Running")
        print("Name: " + name + "; Running: " + str(running) + ".")
        # status information
        container_status_data[name]["running"] = running
        container_status_data[name]["started_at"] = cont.attrs.get("State").get("StartedAt")
        container_status_data[name]["restart_count"] = cont.attrs.get("RestartCount")
        container_status_data[name]["image"] = cont.attrs.get("Config").get("Image")
        container_status_data[name]["ip"] = p_address
        if running:
            # print(ping_ip(p_address, 3))
            pres = ping('127.0.0.1', verbose=False, count=ping_retries)
            ploss = pres.packet_loss
            container_status_data[name]["packet_loss"] = ploss
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


def listen_on_general_queue():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='172.16.3.170'))  # broker ip address --> node manager
    channel = connection.channel()
    channel.exchange_declare(exchange='topics', exchange_type='topic')
    result = channel.queue_declare('')
    queue_name = result.method.queue
    for topic in general_topics_list:
        channel.queue_bind(exchange='topics', queue=queue_name, routing_key=topic)
    channel.basic_consume(queue=queue_name, on_message_callback=general_broker_callback, auto_ack=True)
    # new thread because start_consuming() is blocking
    threading.Thread(target=channel.start_consuming).start()


def listen_on_personal_queue():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='172.16.3.170'))  # broker ip address --> node manager
    channel = connection.channel()
    channel.exchange_declare(exchange='topics', exchange_type='topic')
    result = channel.queue_declare(socket.gethostname())
    queue_name = result.method.queue
    for topic in personal_topics_list:
        channel.queue_bind(exchange='topics', queue=queue_name, routing_key=topic)
    channel.basic_consume(queue=queue_name, on_message_callback=personal_broker_callback, auto_ack=True)
    # new thread because start_consuming() is blocking
    threading.Thread(target=channel.start_consuming).start()


def general_broker_callback(channel, method, properties, body):
    message = body.decode()
    topic = method.routing_key
    print("General callback: Received command on topic " + topic + ", body: " + message)
    if topic == "set_threshold":
        set_threshold(message)
    elif topic == "set_ping_retries":
        set_ping_retries(message)
    elif topic == "set_monitoring_period":
        set_monitoring_period(message)
    elif topic == "status":
        get_container_status(message)


def personal_broker_callback(channel, method, properties, body):
    message = body.decode()
    topic = method.routing_key
    print("Personal callback: Received command on topic " + topic + ", body: " + message)
    if topic == "add_container":
        add_container(message)
    elif topic == "remove_container":
        remove_container(message)


def get_container_status(container_name):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='172.16.3.170'))  # broker ip address --> node manager
    channel = connection.channel()
    channel.exchange_declare(exchange="topics", exchange_type="topic")
    routing_key = "status_response"
    if container_name == "all":
        message = json.dumps(container_status_data).encode()
    elif container_name in container_status_data:
        message = json.dumps(container_status_data[container_name]).encode()
    else:
        message = json.dumps({"error": "Container not found"}).encode()
    channel.basic_publish(exchange="topics", routing_key=routing_key, body=message)
    connection.close()


def add_container(container_name):
    if container_name not in container_status_data:
        container_status_data[container_name] = {}


def remove_container(container_name):
    if container_name in container_status_data:
        del container_status_data[container_name]


def set_threshold(th):
    global threshold
    if 0 <= float(th) <= 100:
        threshold = float(th)


def set_ping_retries(n):
    global ping_retries
    if int(n) >= 0:
        ping_retries = int(n)


def set_monitoring_period(period):
    global monitoring_period
    if int(period) >= 0:
        monitoring_period = int(period)


listen_on_general_queue()
listen_on_personal_queue()
while True:
    try:
        monitor()
        time.sleep(monitoring_period)
    except:
        time.sleep(monitoring_period)
        continue

if __name__ == '__main__':
    client = docker.from_env()
    print(client.containers.list())
