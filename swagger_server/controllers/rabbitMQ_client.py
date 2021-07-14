import json
import threading
import time
import uuid
import pika as pika

HOSTS = 1
TIMEOUT = 2

topics_list = [
    "status_response",
    "containers_list_response"
]

containers_list_responses = {}
status_responses = {}
containers_list_responses_lock = threading.Lock()
status_responses_lock = threading.Lock()

def broker_callback(channel, method, properties, body):
    topic = method.routing_key
    response = str(json.loads(body.decode()))
    if topic == "containers_list_response":
        if "token" in response:
            uuid = response["token"]
            with containers_list_responses_lock:
                if "containers" in response and uuid in containers_list_responses:
                    containers_list_responses[uuid].push(response["containers"])
    if topic == "status_response":
        if "token" in response:
            uuid = response["token"]
            with status_responses_lock:
                if "containers" in response and uuid in status_responses:
                    status_responses[uuid].push(response["containers"])
                elif "container" in response and uuid in status_responses:
                    status_responses[uuid].push(response["container"])
    print("Received command on topic "+method.routing_key+", body: " + response)


def initialize_communication():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='172.16.3.170'))  # broker ip address --> node manager
    channel = connection.channel()
    channel.exchange_declare(exchange='topics', exchange_type='topic')
    result = channel.queue_declare('')
    queue_name = result.method.queue
    for topic in topics_list:
        channel.queue_bind(exchange='topics', queue=queue_name, routing_key=topic)
    channel.basic_consume(queue=queue_name, on_message_callback=broker_callback, auto_ack=True)
    channel.start_consuming()


def send_command(topic, message, queue=""):
    # broker ip address --> node manager
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='172.16.3.170'))
    channel = connection.channel()
    if not queue == "":
        channel.queue_declare(queue=queue)
        topic = queue+topic
    channel.exchange_declare(exchange="topics", exchange_type="topic")
    channel.basic_publish(exchange="topics", routing_key=topic, body=json.dumps(message).encode())
    connection.close()


def add_container(container_name, hostname):
    send_command("add_container", container_name, hostname)


def remove_container(container_name, hostname):
    send_command("remove_container", container_name, hostname)


def set_threshold(th):
    send_command("set_threshold", str(th))


def set_ping_retries(n):
    send_command("set_ping_retries", str(n))


def set_monitoring_period(period):
    send_command("set_monitoring_period", str(period))


def get_container_status(container_name=None, hostname=None):
    print(container_name + " " + hostname)
    request_uuid = str(uuid.uuid4())
    status_responses[uuid] = []
    if hostname is None:
        print("sending command all containers status")
        send_command("all_containers_status", request_uuid)
        start = time.time()
        while True:
            with status_responses_lock:
                if len(status_responses[uuid]) == HOSTS:
                    break
            end = time.time()
            if (end - start) > TIMEOUT:
                print("Timeout scaduto " + str(start) + " " + str(end))
                break
            time.sleep(0.1)
        with status_responses_lock:
            if len(status_responses[uuid]) == 0:
                del status_responses[uuid]
                return None
            else:
                result = []
                for x in status_responses[uuid]:
                    result = result + x
                del status_responses[uuid]
                return result
    else:
        if container_name is None:
            return None
        request = {"token": request_uuid, "container": container_name}
        print("sending command container status")
        send_command("container_status", request, hostname)
        start = time.time()

        while True:
            with status_responses_lock:
                if len(status_responses[uuid]) == 1:
                    break
            end = time.time()
            if (end - start) > TIMEOUT:
                print("Timeout scaduto " + str(start) + " " + str(end))
                break
            time.sleep(0.1)
        with status_responses_lock:
            if len(status_responses[uuid]) == 0:
                del status_responses[uuid]
                return None
            else:
                result = status_responses[uuid][0]
                del status_responses[uuid]
                return result


def get_containers_list():
    request_uuid = str(uuid.uuid4())
    containers_list_responses[uuid] = []
    send_command("container_list", request_uuid)
    start = time.time()
    while True:
        with containers_list_responses_lock:
            if len(containers_list_responses[uuid]) == HOSTS:
                break
        end = time.time()
        if (end - start) > TIMEOUT:
            break
        time.sleep(0.1)
    with containers_list_responses_lock:
        if len(containers_list_responses[uuid]) == 0:
            del containers_list_responses[uuid]
            return None
        else:
            result = []
            for x in containers_list_responses[uuid]:
                result = result + x
            del containers_list_responses[uuid]
            return result


broker_thread = threading.Thread(target=initialize_communication)
broker_thread.start()
