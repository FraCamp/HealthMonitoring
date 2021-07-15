import json
import socket
import docker
import pika as pika
from pythonping import ping
import threading
import time

client = docker.from_env()
list = client.containers.list(all=True)
hostname = socket.gethostname()
threshold = 60.0
ping_retries = 3
monitoring_period = 2
monitored_containers_status = {}  # list of monitored containers
general_topics_list = [
    "set_threshold",
    "set_ping_retries",
    "set_monitoring_period",
    "all_containers_status",
    "container_list",
    "config"
]
personal_topics_list = [
    "add_container",
    "remove_container",
    "container_status"
]


def monitor():
    for name in monitored_containers_status.keys():
        local_name = monitored_containers_status[name]["local_name"]
        try:
            print(local_name)
            cont = client.containers.get(local_name)
        except:
            continue
        if cont is None:
            print("container is none")
            continue
        cont.reload()
        p_address = cont.attrs['NetworkSettings']['IPAddress']
        running = cont.attrs.get("State").get("Running")
        print("Name: " + local_name + "; Running: " + str(running) + ".")
        # status information
        monitored_containers_status[name]["running"] = running
        monitored_containers_status[name]["started_at"] = cont.attrs.get("State").get("StartedAt")
        monitored_containers_status[name]["restart_count"] = cont.attrs.get("RestartCount")
        monitored_containers_status[name]["image"] = cont.attrs.get("Config").get("Image")
        monitored_containers_status[name]["ip"] = p_address
        if running:
            # print(ping_ip(p_address, 3))
            pres = ping(p_address, verbose=False, count=ping_retries)
            ploss = pres.packet_loss
            monitored_containers_status[name]["packet_loss"] = ploss
            if not pres.success():
                print("Ping failed!")
                print("Restarting container.")
                cont.restart()
            elif ploss * 100 > threshold:
                print("Packet Loss: " + str(ploss * 100) + " %")
                print("Restarting container.")
                cont.restart()
            else:
                print("Healthy container!")
                print("Packet Loss: " + str(ploss * 100) + " %")
        else:
            print(local_name + " is down!")
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
    print("channel queue = " + queue_name)
    threading.Thread(target=channel.start_consuming).start()


def listen_on_personal_queue():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='172.16.3.170'))  # broker ip address --> node manager
    channel = connection.channel()
    channel.exchange_declare(exchange='topics', exchange_type='topic')
    channel.queue_declare(hostname)
    for topic in personal_topics_list:
        print(hostname + topic)
        channel.queue_bind(exchange='topics', queue=hostname, routing_key=hostname + topic)
    channel.basic_consume(queue=hostname, on_message_callback=personal_broker_callback, auto_ack=True)
    # new thread because start_consuming() is blocking
    threading.Thread(target=channel.start_consuming).start()


def get_configuration(message):
    print("in config")
    result = {"token": message,
              "config": {"threshold": threshold, "ping-retries": ping_retries, "monitoring-period": monitoring_period}}
    print(str(result))
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='172.16.3.170'))  # broker ip address --> node manager
    channel = connection.channel()
    channel.exchange_declare(exchange="topics", exchange_type="topic")
    routing_key = "config_response"
    message = json.dumps(result).encode()
    channel.basic_publish(exchange="topics", routing_key=routing_key, body=message)
    connection.close()
    print("sent")


def general_broker_callback(channel, method, properties, body):
    if body is None:
        message = None
    else:
        message = json.loads(body.decode())
    topic = method.routing_key
    print("General callback: Received command on topic " + topic + ", body: " + str(message))
    if topic == "set_threshold":
        set_threshold(message)
    elif topic == "set_ping_retries":
        set_ping_retries(message)
    elif topic == "set_monitoring_period":
        set_monitoring_period(message)
    elif topic == "all_containers_status":
        get_all_monitored_containers_status(message)
    elif topic == "container_list":
        get_all_containers(message)
    elif topic == "config":
        get_configuration(message)


def personal_broker_callback(channel, method, properties, body):
    if body is None:
        message = None
    else:
        message = json.loads(body.decode())
    topic = method.routing_key
    print("Personal callback: Received command on topic " + topic + ", body: " + str(message))
    if topic == hostname + "add_container":
        add_container(message)
    elif topic == hostname + "remove_container":
        remove_container(message)
    elif topic == hostname + "container_status":
        get_monitored_container_status(message)


def get_monitored_container_status(request):
    if "token" in request:
        uuid = request["token"]
        if "container" in request:
            container_name = hostname + "-" + request["container"]
            # broker ip address --> node manager
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='172.16.3.170'))
            channel = connection.channel()
            channel.exchange_declare(exchange="topics", exchange_type="topic")
            routing_key = "status_response"
            if container_name in monitored_containers_status:
                result = {"token": uuid, "container": monitored_containers_status[container_name]}
                message = json.dumps(result).encode()
            else:
                message = json.dumps({"container": None, "token": uuid}).encode()
            channel.basic_publish(exchange="topics", routing_key=routing_key, body=message)
            print(str(message))
            connection.close()


def get_all_monitored_containers_status(uuid):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='172.16.3.170'))
    channel = connection.channel()
    channel.exchange_declare(exchange="topics", exchange_type="topic")
    routing_key = "status_response"
    result = {"token": uuid, "containers": monitored_containers_status}
    message = json.dumps(result).encode()
    channel.basic_publish(exchange="topics", routing_key=routing_key, body=message)
    print(str(message))
    connection.close()


def get_all_containers(uuid):
    names = []
    result = {"token": uuid}
    container_list = client.containers.list()
    for c in container_list:
        names.append(hostname + c.attrs.get("Name").replace("/", "-"))
    result["containers"] = names
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='172.16.3.170'))  # broker ip address --> node manager
    channel = connection.channel()
    channel.exchange_declare(exchange="topics", exchange_type="topic")
    routing_key = "containers_list_response"
    message = json.dumps(result).encode()
    channel.basic_publish(exchange="topics", routing_key=routing_key, body=message)
    connection.close()


def add_container(container_name):
    composite_name = hostname + "-" + container_name
    if composite_name not in monitored_containers_status:
        monitored_containers_status[composite_name] = {"local_name": container_name}


def remove_container(container_name):
    composite_name = hostname + "-" + container_name
    if composite_name in monitored_containers_status:
        del monitored_containers_status[composite_name]


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


if __name__ == '__main__':
    listen_on_general_queue()
    listen_on_personal_queue()
    while True:
        try:
            monitor()
            time.sleep(monitoring_period)
        except Exception as e:
            time.sleep(monitoring_period)
            print(str(e))
            continue
