import json
import sys
import threading
import time
import uuid
import pika as pika

HOSTS = 3
TIMEOUT = 4

topics_list = [
    "status_response",
    "containers_list_response",
    "config_response"
]

containers_list_responses = {}
status_responses = {}
config_responses = {}
containers_list_responses_lock = threading.Lock()
status_responses_lock = threading.Lock()
config_responses_lock = threading.Lock()


def broker_callback(channel, method, properties, body):
    topic = method.routing_key
    response = json.loads(body.decode())
    if topic == "containers_list_response":
        if "token" in response:
            uuid = response["token"]
            with containers_list_responses_lock:
                if "containers" in response and uuid in containers_list_responses:
                    print("Adding containers to dictionary, containers: " + str(response["containers"]),
                          file=sys.stderr)
                    containers_list_responses[uuid].append(response["containers"])
                    print("dictionary: " + str(containers_list_responses), file=sys.stderr)
    if topic == "status_response":
        if "token" in response:
            uuid = response["token"]
            with status_responses_lock:
                if "containers" in response and uuid in status_responses:
                    values = response["containers"].values()
                    values_list = list(values)
                    status_responses[uuid].append(values_list)
                elif "container" in response and uuid in status_responses:
                    status_responses[uuid].append(response["container"])
    if topic == "config_response":
        if "token" in response:
            uuid = response["token"]
            with config_responses_lock:
                if "config" in response and uuid in config_responses:
                    print("Adding containers to dictionary, containers: " + str(response["config"]),
                          file=sys.stderr)
                    config_responses[uuid].append(response["config"])
                    print("dictionary: " + str(config_responses), file=sys.stderr)
    print("Received command on topic " + method.routing_key + ", body: " + str(response), file=sys.stderr)


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
        topic = queue + topic
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
    if container_name is not None and hostname is not None:
        print(container_name + " " + hostname, file=sys.stderr)
    request_uuid = str(uuid.uuid4())
    status_responses[request_uuid] = []
    if hostname is None:
        print("sending command all containers status", file=sys.stderr)
        send_command("all_containers_status", request_uuid)
        start = time.time()
        while True:
            with status_responses_lock:
                if len(status_responses[request_uuid]) == HOSTS:
                    break
            end = time.time()
            if (end - start) > TIMEOUT:
                print("Timeout scaduto " + str(start) + " " + str(end), file=sys.stderr)
                break
            time.sleep(0.1)
        with status_responses_lock:
            if len(status_responses[request_uuid]) == 0:
                del status_responses[request_uuid]
                return None
            else:
                result = []
                for x in status_responses[request_uuid]:
                    print(str(x), file=sys.stderr)
                    result = result + x
                del status_responses[request_uuid]
                return result
    else:
        if container_name is None:
            return None
        request = {"token": request_uuid, "container": container_name}
        print("sending command container status", file=sys.stderr)
        send_command("container_status", request, hostname)
        start = time.time()

        while True:
            with status_responses_lock:
                if len(status_responses[request_uuid]) == 1:
                    break
            end = time.time()
            if (end - start) > TIMEOUT:
                print("Timeout scaduto " + str(start) + " " + str(end), file=sys.stderr)
                break
            time.sleep(0.1)
        with status_responses_lock:
            if len(status_responses[request_uuid]) == 0:
                del status_responses[request_uuid]
                return None
            else:
                result = status_responses[request_uuid][0]
                del status_responses[request_uuid]
                return result


def get_containers_list():
    request_uuid = str(uuid.uuid4())
    containers_list_responses[request_uuid] = []
    send_command("container_list", request_uuid)
    start = time.time()
    end = time.time()
    while True:
        with containers_list_responses_lock:
            if len(containers_list_responses[request_uuid]) == HOSTS:
                break
        end = time.time()
        if (end - start) > TIMEOUT:
            break
        time.sleep(0.1)
    if (end - start) > TIMEOUT:
        print("timeout scaduto", file=sys.stderr)
    with containers_list_responses_lock:
        print("dictionary: " + str(containers_list_responses), file=sys.stderr)
        print("len: " + str(len(containers_list_responses)), file=sys.stderr)
        if len(containers_list_responses[request_uuid]) == 0:
            del containers_list_responses[request_uuid]
            return None
        else:
            result = []
            for x in containers_list_responses[request_uuid]:
                result = result + x
            del containers_list_responses[request_uuid]
            print("result " + str(result), file=sys.stderr)
            return result


def get_configuration():
    request_uuid = str(uuid.uuid4())
    config_responses[request_uuid] = []
    send_command("config", request_uuid)
    start = time.time()
    end = time.time()
    while True:
        with config_responses_lock:
            if len(config_responses[request_uuid]) == HOSTS:
                break
        end = time.time()
        if (end - start) > TIMEOUT:
            break
        time.sleep(0.1)
    if (end - start) > TIMEOUT:
        print("timeout scaduto", file=sys.stderr)
    with config_responses_lock:
        print("dictionary: " + str(config_responses), file=sys.stderr)
        print("len: " + str(len(config_responses)), file=sys.stderr)
        if len(config_responses[request_uuid]) == 0:
            del config_responses[request_uuid]
            return None
        else:
            result = []
            for x in config_responses[request_uuid]:
                result.append(x)
            del config_responses[request_uuid]
            print("result " + str(result), file=sys.stderr)
            return result


broker_thread = threading.Thread(target=initialize_communication)
broker_thread.start()
