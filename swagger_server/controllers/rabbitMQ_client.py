import json
import threading
import time
import uuid
import pika as pika

HOSTS = 3

topics_list = [
    "status_response",
    "containers_list_response"
]

containers_list_responses = {}


def broker_callback(channel, method, properties, body):
    response = str(json.loads(body.decode()))
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
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='172.16.3.170'))  # broker ip address --> node manager
    channel = connection.channel()
    if not queue == "":
        channel.queue_declare(queue=queue)
        topic = queue+topic
    channel.exchange_declare(exchange="topics", exchange_type="topic")
    channel.basic_publish(exchange="topics", routing_key=topic, body=message.encode())
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


def get_container_status(name):
    send_command("status", name)


def get_containers_list():
    request_uuid = str(uuid.uuid4())
    containers_list_responses[uuid] = []
    send_command("container_list", request_uuid)


broker_thread = threading.Thread(target=initialize_communication)
broker_thread.start()
