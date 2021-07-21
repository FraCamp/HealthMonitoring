import json
import os
import docker
import pika as pika
from pythonping import ping
import threading
import time

from typing import List, Any

client = docker.from_env()

# get the name of the host as an environment variable that is set within the docker run command.
hostname = os.environ["HOSTNAME"]

# initial values for the monitoring configuration
threshold = 60.0  # tolerated packet loss percentage
ping_retries = 3  # number of packets sent when trying to reach a monitored container
monitoring_period = 2  # seconds between each monitoring cycle

# dictionary indexed by container name, with
# the data associated to each monitored container
monitored_containers_status = {}

# list of topics for the general queue
general_topics = [
    "set_threshold",
    "set_ping_retries",
    "set_monitoring_period",
    "all_containers_status",
    "container_list",
    "config"
]

# list of topics for the personal queue
# the name of the host is prepended so that the personal queue will only deliver messages
# that are actually intended for the host in which the agent is running
personal_topics = [
    hostname + "add_container",
    hostname + "remove_container",
    hostname + "container_status"
]

# ip address of the host running the rabbitMQ broker
rabbitMQ_broker_address = '172.16.3.170'


def monitor() -> None:
    """
      Checks the status of the monitored containers on the host and updates the local
      information about each container. If the container has been stopped or is
      experiencing network issues, it is restarted.
    """

    # We iterate on all the monitored containers
    for name in monitored_containers_status.keys():
        # we retrieve the local name from the dictionary
        local_name = monitored_containers_status[name]["local_name"]

        try:
            # We try to find the container on the host.
            container = client.containers.get(local_name)
        except:
            continue
        if container is None:
            # If the container is not found on the host, we just ignore its name
            continue

        # We reload the attributes of the container, since they might be cached.
        container.reload()

        # We retrieve various information about the container. Its IP address, its execution state
        # (if it is running or not), the start time and the times it was restarted, and the name of
        # the docker image of the container.
        p_address = container.attrs['NetworkSettings']['IPAddress']
        running = container.attrs.get("State").get("Running")
        print("Name: " + local_name + "; Running: " + str(running) + ".")
        # status information
        monitored_containers_status[name]["running"] = running
        monitored_containers_status[name]["started_at"] = container.attrs.get("State").get("StartedAt")
        monitored_containers_status[name]["restart_count"] = container.attrs.get("RestartCount")
        monitored_containers_status[name]["image"] = container.attrs.get("Config").get("Image")
        monitored_containers_status[name]["ip"] = p_address

        if running:
            # If the container is running, we try to ping it to see whether
            # it replies or not, and with which packet loss percentage. For the ping
            # operation, we exploited the pythonping module.
            pres = ping(p_address, verbose=False, count=ping_retries)
            ploss = pres.packet_loss
            monitored_containers_status[name]["packet_loss"] = ploss * 100

            # if the ping did not succeed we restart the container
            if not pres.success():
                print("Ping failed!")
                print("Restarting container.")
                container.restart()

            # if the packet loss percentage is higher than a set threshold, we restart the container
            elif ploss * 100 > threshold:
                print("Packet Loss: " + str(ploss * 100) + " %")
                print("Restarting container.")
                container.restart()

            # if everything is alright, we just print some diagnostic messages.
            else:
                print("Healthy container!")
                print("Packet Loss: " + str(ploss * 100) + " %")

        else:
            # if the container is not running, we try to restart it
            print(local_name + " is down!")
            container.restart()


def listen_on_queue(broker: str, topics: List[str], queue: str = '', callback: Any = None) -> None:
    """
      Opens a connection with a rabbitMQ broker running on the specified host. Declares a queue with
      the provided name and binds it to the provided topics. Sets the provided callback as the handler
      to call when a new message is received on the queue.

      :param broker: The ip address of the host running the rabbitMQ broker, as a string
      :param queue: The name of the desired queue
      :param topics: The list of topics on which the queue must be bind
      :param callback: A method to call when a new message is received. It must have the form: handler(channel, method, properties, body) -> None
    """
    if topics is None:
        topics = []

    # We open the connection with the RabbitMQ broker and declare a
    # queue with the name provided as parameter
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(broker))
    channel = connection.channel()
    channel.exchange_declare(exchange='topics', exchange_type='topic')
    result = channel.queue_declare(queue)
    if queue == '':
        queue = result.method.queue

    # We bind the queue to all the topics provided as parameter
    for topic in topics:
        channel.queue_bind(exchange='topics', queue=queue, routing_key=topic)

    # We set the callback to be called for messages received on the queue.
    channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=True)

    # We start listening on the queue in a new thread, because start_consuming() is
    # a blocking function.
    threading.Thread(target=channel.start_consuming).start()


def listen_on_general_queue() -> None:
    """
      Opens a connection with a rabbitMQ broker. Declares a queue
      and binds it to the topics in the general_topics list. Sets the general_broker_callback function
      as the handler for new messages.
    """
    listen_on_queue(rabbitMQ_broker_address, general_topics, callback=general_broker_callback)


def listen_on_personal_queue() -> None:
    """
      Opens a connection with a rabbitMQ broker. Declares a queue
      names as the host running the agent and binds it to the topics in the personal_topics list.
      Sets the personal_broker_callback function as the handler for new messages.
    """
    listen_on_queue(rabbitMQ_broker_address, personal_topics, hostname, personal_broker_callback)


def send_message(broker: str, topic: str, body: Any) -> None:
    """
      Opens a connection with a rabbitMQ broker to send a message, then closes the connection.

      :param broker: the ip address of the broker
      :param topic: the topic related to the message
      :param body: the content of the message body
    """
    # We open the connection with a rabbitMQ broker.
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=broker))
    channel = connection.channel()
    channel.exchange_declare(exchange="topics", exchange_type="topic")

    # We encode the message in json format (needed since we sometimes need to send complex
    # objects like dictionaries and lists). We then encode the message in bytes and send it with the topic
    # provided as parameter, closing the connection at the end.
    message = json.dumps(body).encode()
    channel.basic_publish(exchange="topics", routing_key=topic, body=message)
    connection.close()


def send_configuration(message: str) -> None:
    """
        Sends a rabbitMQ message with the current monitoring parameters.
    """
    result = {"token": message,
              "config": {"name": hostname, "threshold": threshold, "ping-retries": ping_retries,
                         "monitoring-period": monitoring_period}}
    send_message(rabbitMQ_broker_address, "config_response", result)


def general_broker_callback(channel, method, properties, body) -> None:
    """
      Callback method for all requests received on the general queue.
    """
    # We decode the message and parse it from json format.
    if body is None:
        message = None
    else:
        message = json.loads(body.decode())

    # We check the topic of the message, on which the actions to be done depend.
    topic = method.routing_key
    print("General callback: Received command on topic " + topic + ", body: " + str(message))
    if topic == "set_threshold":
        set_threshold(message)
    elif topic == "set_ping_retries":
        set_ping_retries(message)
    elif topic == "set_monitoring_period":
        set_monitoring_period(message)
    elif topic == "all_containers_status":
        send_all_monitored_containers_status(message)
    elif topic == "container_list":
        send_all_containers(message)
    elif topic == "config":
        send_configuration(message)


def personal_broker_callback(channel, method, properties, body):
    """
          Callback method for all requests received on the general queue.
        """
    # We decode the message and parse it from json format.
    if body is None:
        message = None
    else:
        message = json.loads(body.decode())

    # We check the topic of the message, on which the actions to be done depend.
    topic = method.routing_key
    print("Personal callback: Received command on topic " + topic + ", body: " + str(message))
    if topic == hostname + "add_container":
        add_container(message)
    elif topic == hostname + "remove_container":
        remove_container(message)
    elif topic == hostname + "container_status":
        if "token" in message:
            uuid = message["token"]
            if "container" in message:
                container_name = message["container"]
                send_monitored_container_status(uuid, container_name)


def send_monitored_container_status(token: str, container_name: str) -> None:
    """
        Sends a rabbitMQ message with the status of the requested container.

        :param token: the request id, used to link the response with the request
        :param container_name: the name of the requested container
    """

    # We prepend the name of the host to the name of the container. This makes the container name
    # unique in the whole cluster.
    container_name = hostname + "-" + container_name

    # If the container is found between the list of monitored containers, its status is inserted in the
    # container field of the dictionary sent as message. Otherwise, the container field is set to None.
    # The received token is sent as part of the message, so that the manager knows the request to which this
    # message is replying.
    if container_name in monitored_containers_status:
        message = {"token": token, "container": monitored_containers_status[container_name]}
    else:
        message = {"container": None, "token": token}
    send_message(rabbitMQ_broker_address, 'status_response', message)


def send_all_monitored_containers_status(token: str) -> None:
    """
        Sends a rabbitMQ message with the status of all the monitored containers.

        :param token: the request id, used to link the response with the request
    """
    result = {"token": token, "containers": monitored_containers_status}
    send_message(rabbitMQ_broker_address, "status_response", result)


def send_all_containers(token: str) -> None:
    """
        Sends a rabbitMQ message with the list of all active containers on the host.

        :param token: the request id, used to link the response with the request
    """
    names = []

    # The received token is sent as part of the message, so that the manager knows the request to which this
    # message is replying.
    result = {"token": token}

    # We retrieve the list of active containers on the host and append the names to a local list.
    # The names are edited to contain the name of the host, so that a container name is unique in the
    # cluster.
    container_list = client.containers.list()
    for c in container_list:
        names.append(hostname + c.attrs.get("Name").replace("/", "-"))
    result["containers"] = names

    # We send the message with the list
    send_message(rabbitMQ_broker_address, "containers_list_response", result)


def add_container(container_name: str) -> None:
    """
        Adds a container to the list of monitored containers of the agent.

        :param container_name: The name of the container to add
    """

    # We compute the full name of the container, that includes the name of the host,
    # so that a container name is unique in the cluster. Then we add the key in the
    # monitored_containers_status dictionary, so it will be considered in the next monitoring cycle.
    composite_name = hostname + "-" + container_name
    if composite_name not in monitored_containers_status:
        monitored_containers_status[composite_name] = {"local_name": container_name}


def remove_container(container_name) -> None:
    """
        Removes a container from the list of monitored containers of the agent.

        :param container_name: The name of the container to remove
    """

    # We compute the full name of the container, that includes the name of the host,
    # so that a container name is unique in the cluster. Then we remove the key from the
    # monitored_containers_status dictionary, so it will not be considered in the next monitoring cycles.
    composite_name = hostname + "-" + container_name
    if composite_name in monitored_containers_status:
        del monitored_containers_status[composite_name]


def set_threshold(new_threshold: float) -> None:
    """
        Sets a new tolerated packet loss threshold.

        :param new_threshold: The new tolerated packet loss value. Must be between 0 and 100.
    """
    global threshold
    if 0 <= float(new_threshold) <= 100:
        threshold = float(new_threshold)


def set_ping_retries(new_ping_retries: int) -> None:
    """
        Sets a new value for the number of packets to send when trying to reach a container.

        :param new_ping_retries: The new value for the ping_retries configuration parameter. Must be higher than 0.
    """
    global ping_retries
    if int(new_ping_retries) >= 0:
        ping_retries = int(new_ping_retries)


def set_monitoring_period(period: int) -> None:
    """
        Sets a new value for the interval between monitoring cycles.

        :param period: The new value for the interval between monitoring cycles. Must be higher than 0.
    """
    global monitoring_period
    if int(period) >= 0:
        monitoring_period = int(period)


if __name__ == '__main__':
    # At the beginning of the agent script, we start listening on the two queues that the agent requires:
    # the personal queue and the general queue. We need to do this to receive requests.
    listen_on_general_queue()
    listen_on_personal_queue()

    # The agent then enters an infinite loop in which it periodically checks some attributes of the monitored
    # containers. The monitor function is wrapped in a try catch block to avoid terminating the agent in case
    # some errors occur.
    while True:
        try:
            monitor()
            time.sleep(monitoring_period)
        except Exception as e:
            time.sleep(monitoring_period)
            continue
