import json
import sys
import threading
import time
import uuid
from typing import List, Any, Callable, Optional

import pika as pika

# Number of hosts in the cluster
HOSTS = 3

# Maximum time, in seconds, to wait when expecting to receive responses by the agents after
# sending a request
TIMEOUT = 4

# list of topics to listen
topics_list = [
    "status_response",
    "containers_list_response",
    "config_response"
]

# dictionaries for aggregating the responses of the various hosts, when a request for all the hosts is sent
containers_list_responses = {}
status_responses = {}
config_responses = {}

# lock objects used to guarantee mutual exclusion when manipulating the dictionaries above. This is important since
# the dictionaries can be accessed from different functions that are called in an asynchronous way by the REST server.
containers_list_responses_lock = threading.Lock()
status_responses_lock = threading.Lock()
config_responses_lock = threading.Lock()

# ip address of the host running the rabbitMQ broker
rabbitMQ_broker_address = '172.16.3.170'


def broker_callback(channel, method, properties, body) -> None:
    """
      Callback method for all messages received.
    """

    # We decode the message and parse it from json format.
    if body is None:
        response = None
    else:
        response = json.loads(body.decode())

    # We check the topic of the message, on which the actions to be done depend.
    topic = method.routing_key
    if topic == "containers_list_response":
        # this topic means that the message is a response to a request for the complete list of
        # containers running on the cluster. This response comes from one of the hosts in the cluster.
        # The token in the response is the same that was previously sent in the request, so it is used to identify
        # the correct entry of the dictionary in which the response must be inserted, so it can be merged with other
        # responses to the same request.
        if "token" in response:
            token = response["token"]

            # the lock is used to ensure mutual exclusion while manipulating the containers_list_responses dictionary
            with containers_list_responses_lock:
                if "containers" in response and token in containers_list_responses:
                    # the list of containers name is appended to the correct entry of the containers_list_responses
                    # dictionary
                    containers_list_responses[token].append(response["containers"])

    if topic == "status_response":
        # a message with this topic is received in two cases only: when the message is a response to a request
        # for the status of all the containers monitored on the cluster, and when it is a response to the request of
        # the status of a specific monitored container in the cluster. This response comes from one of the hosts in
        # the cluster.
        # The token in the response is the same that was previously sent in the request, so it is used to identify
        # the correct entry of the dictionary in which the response must be inserted, so it can be merged with other
        # eventual responses to the same request.
        if "token" in response:
            token = response["token"]

            # the lock is used to ensure mutual exclusion while manipulating the status_responses dictionary
            with status_responses_lock:

                if "containers" in response and token in status_responses:
                    # if the response contains a "containers" field, then it is a response to a request
                    # for the status of all the containers monitored on the cluster. We append the list of
                    # dictionaries, each one with the data about one of the containers to the correct entry
                    # of the status_responses dictionary
                    values = response["containers"].values()
                    values_list = list(values)
                    status_responses[token].append(values_list)

                elif "container" in response and token in status_responses:
                    # if the response contains a "container" field, then it is a response to the request of
                    # the status of a specific monitored container in the cluster. We append the
                    # dictionary, containing the data about one of the containers to the correct entry
                    # of the status_responses dictionary
                    status_responses[token].append(response["container"])

    if topic == "config_response":
        # this topic means that the message is a response to a request for the configuration
        # parameters on all the agents in the cluster. This response comes from one of the hosts in the cluster.
        # The token in the response is the same that was previously sent in the request, so it is used to identify
        # the correct entry of the dictionary in which the response must be inserted, so it can be merged with other
        # responses to the same request.
        if "token" in response:
            token = response["token"]

            # the lock is used to ensure mutual exclusion while manipulating the config_responses dictionary
            with config_responses_lock:
                if "config" in response and token in config_responses:
                    # the dictionary, containing the current configuration of one agent,
                    # is appended to the correct entry of the config_responses
                    # dictionary
                    config_responses[token].append(response["config"])
    print("Received command on topic " + method.routing_key + ", body: " + str(response), file=sys.stderr)


def initialize_communication(broker: str, topics: List[str], callback: Any = None) -> None:
    """
      Opens a connection with a rabbitMQ broker running on the specified host. Declares a queue
      and binds it to the provided topics. Sets the provided callback as the handler
      to call when a new message is received on the queue.

      :param broker: The ip address of the host running the rabbitMQ broker, as a string
      :param topics: The list of topics on which the queue must be bind
      :param callback: A method to call when a new message is received. It must have the form: handler(channel, method, properties, body) -> None
    """
    # We open the connection with the RabbitMQ broker and declare a
    # queue
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=broker))  # broker ip address --> node manager
    channel = connection.channel()
    channel.exchange_declare(exchange='topics', exchange_type='topic')
    result = channel.queue_declare('')
    queue_name = result.method.queue

    # We bind the queue to all the topics provided as parameter
    for topic in topics:
        channel.queue_bind(exchange='topics', queue=queue_name, routing_key=topic)

    # We set the callback to be called for messages received on the queue.
    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    # We start listening on the queue in a new thread, because start_consuming() is
    # a blocking function
    threading.Thread(target=channel.start_consuming).start()


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


def add_container(container_name: str, hostname: str) -> None:
    """
          Sends a message to a agent and requests that a container is added to the
          monitored containers.

          :param container_name: the name of the container to add
          :param hostname: the name of the host on which the container runs
    """
    # prepends the name of the agent's host to the topic, to use the topic of that specific
    # host and avoid sending the message to all agents.
    send_message(rabbitMQ_broker_address, hostname + "add_container", container_name)


def remove_container(container_name: str, hostname: str) -> None:
    """
      Sends a message to a agent and requests that a container is removed from the
      monitored containers.

      :param container_name: the name of the container to remove
      :param hostname: the name of the host on which the container runs
    """
    # prepends the name of the agent's host to the topic, to use the topic of that specific
    # host and avoid sending the message to all agents.
    send_message(rabbitMQ_broker_address, hostname + "remove_container", container_name)


def set_threshold(threshold: float) -> None:
    """
      Sends a message to all agents, setting a new value for their packet loss threshold
      parameter.

      :param threshold: the new value for the threshold parameter
    """
    send_message(rabbitMQ_broker_address, "set_threshold", str(threshold))


def set_ping_retries(ping_retries: int) -> None:
    """
      Sends a message to all agents, setting a new value for their ping_retries
      parameter. That is, the number of packets sent to a container when trying to
      reach it for diagnostic reasons.

      :param ping_retries: the new value for the ping_retries parameter
    """
    send_message(rabbitMQ_broker_address, "set_ping_retries", str(ping_retries))


def set_monitoring_period(period: int) -> None:
    """
      Sends a message to all agents, setting a new value for their monitoring period
      parameter.

      :param period: the new value for the monitoring period
    """
    send_message(rabbitMQ_broker_address, "set_monitoring_period", str(period))


def await_and_merge_responses(request_token: str,
                              expected_responses: int,
                              merge_dictionary: dict,
                              merge_function: Callable[[Any], Any],
                              lock: threading.Lock,
                              timeout: int) -> Optional[list]:
    """
      Utility function that awaits for a certain number of responses to a
      specific request. Then it merges the received responses in an unique object
      using a custom method passed as parameter. It exploits a lock to manage the
      dictionary of responses in mutual exclusion.
      A timeout must be provided: when it elapses and the number of responses does not
      match the expected number, a partial result is returned.

      :param request_token: the request token, used to access the correct entry of the merge_dictionary
      :param expected_responses: the number of responses that the request should receive
      :param merge_dictionary: a dictionary in which the responses should eventually be found
      :param merge_function: a function that must be used to merge the different responses into a single response
      :param lock: the lock that must be used when accessing the merge_dictionary to avoid conflicts
      :param timeout: the maximum amount of time to wait for responses
    """

    # We save the starting time in a local variable, so we can check whether the timeout
    # is elapsed during execution.
    start = time.time()
    end = time.time()

    while True:
        # We periodically check if the merge_dictionary contains expected_responses values associated
        # with the request of interest. If this is true, we received all responses and we can proceed
        # with merging them and returning the result.
        with lock:
            if len(merge_dictionary[request_token]) == expected_responses:
                break

        # If it is not true, we check if the timeout is elapsed, in which case we leave the loop.
        # Otherwise we sleep for some milliseconds and continue with the loop.
        end = time.time()
        if (end - start) > timeout:
            break
        time.sleep(0.1)

    # Since we are outside the loop, we check the reason of exit. If the exit was caused by
    # the timeout, we print an error message.
    if (end - start) > timeout:
        print("Timeout elapsed on request " + request_token, file=sys.stderr)

    with lock:
        # If we don't find any response in the dictionary, we just delete the request's entry
        # and return None, since the timeout is surely elapsed in this case, and no host responded.
        if len(merge_dictionary[request_token]) == 0:
            del merge_dictionary[request_token]
            return None
        else:
            # If we find at least one response, we merge the responses and delete the request's entry
            # in the dictionary, then we return the result, partial or complete.
            result = merge_function(merge_dictionary[request_token])
            del merge_dictionary[request_token]
            return result


def merge_containers_status(lists: List[List[dict]]) -> List[dict]:
    """
      Utility function used to merge the responses to the containers status request into a
      single list.

      :param lists: the list of responses, each containing a list of dictionaries that represent the status of different containers
    """
    result = []
    for x in lists:
        result = result + x
    return result


def merge_container_status(responses: List[dict]) -> Optional[dict]:
    """
      Utility function used to obtain a single response to the container status request.

      :param responses: the list of responses, that should in any case only contain one response.
    """
    if len(responses) > 0:
        return responses[0]
    return None


def get_container_status(container_name=None, hostname=None) -> Any:
    """
      Sends a request for the status of one or all the containers, depending on the parameters.
      Then it awaits for all the expected responses and merges them into a single result that is
      returned.

      :param hostname: the name of the host on which the requested container runs. If this is left empty, a request for the status of all the containers will be sent.
      :param container_name: the name of the container of which the status is requested. This parameter is ignored if hostname is left empty.

      :return: a dictionary containing information about one container, if a container name is passed as parameter; a list of dictionary containing information about all the monitored containers otherwise
    """

    # We generate a random token for the request and initialize a entry in the status_responses
    # dictionary.
    request_uuid = str(uuid.uuid4())
    status_responses[request_uuid] = []

    if hostname is None:
        # if the hostname was not provided as parameter, we request the status of all the
        # containers, and we return the responses aggregated in a single result.
        send_message(rabbitMQ_broker_address, "all_containers_status", request_uuid)
        result = await_and_merge_responses(request_token=request_uuid,
                                           expected_responses=HOSTS,
                                           merge_dictionary=status_responses,
                                           merge_function=merge_containers_status,
                                           lock=status_responses_lock,
                                           timeout=TIMEOUT
                                           )
        return result
    else:
        # otherwise, if also a container name is present, we request the status of a single container
        # running on a host
        if container_name is None:
            return None

        # we insert the token in the request and send it to the specified host, prepending its name
        # to the topic. Then, we return the received response.
        request = {"token": request_uuid, "container": container_name}
        send_message(rabbitMQ_broker_address, hostname + "container_status", request)
        result = await_and_merge_responses(request_token=request_uuid,
                                           expected_responses=1,
                                           merge_dictionary=status_responses,
                                           merge_function=merge_container_status,
                                           lock=status_responses_lock,
                                           timeout=TIMEOUT
                                           )
        return result


def merge_containers_lists(lists: List[List[str]]) -> List[str]:
    """
      Utility function used to merge the responses to the containers list request into a
      single list.

      :param lists: the list of responses, each containing a list of container names
    """
    result = []
    for x in lists:
        result = result + x
    return result


def get_containers_list():
    """
      Sends a request for the list of all the names of containers running on all hosts of the cluster.
      Then it awaits for all the expected responses and merges them into a single list that is
      returned.
    """
    # We generate a random token for the request and initialize a entry in the status_responses
    # dictionary.
    request_uuid = str(uuid.uuid4())
    containers_list_responses[request_uuid] = []

    # we request the list of all the names of containers running in the cluster,
    # and we return the responses aggregated in a single result.
    send_message(rabbitMQ_broker_address, "container_list", request_uuid)
    result = await_and_merge_responses(request_token=request_uuid,
                                       expected_responses=HOSTS,
                                       merge_dictionary=containers_list_responses,
                                       merge_function=merge_containers_lists,
                                       lock=containers_list_responses_lock,
                                       timeout=TIMEOUT
                                       )
    return result


def merge_configurations(configurations: List[dict]) -> List[dict]:
    """
      Utility function used to merge the responses to the configuration request into a
      single list.

      :param configurations: the list of responses, each containing a dictionary representing the current configuration on a container.
    """
    # this just return the parameter as it is, the function only exists to match the pattern of the
    # await_and_merge_responses function defined above.
    return configurations


def get_configuration():
    """
      Sends a request for the current configuration of all active agents.
      Then it awaits for all the expected responses and merges them into a single list that is
      returned.
    """
    # We generate a random token for the request and initialize a entry in the status_responses
    # dictionary.
    request_uuid = str(uuid.uuid4())
    config_responses[request_uuid] = []

    # we request the configuration of all the agents in the cluster,
    # and we return the responses aggregated in a single result.
    send_message(rabbitMQ_broker_address, "config", request_uuid)
    result = await_and_merge_responses(request_token=request_uuid,
                                       expected_responses=HOSTS,
                                       merge_dictionary=config_responses,
                                       merge_function=merge_configurations,
                                       lock=config_responses_lock,
                                       timeout=TIMEOUT
                                       )
    return result


# we initialize the communication in order to listen for responses to our requests.
initialize_communication(rabbitMQ_broker_address, topics_list, broker_callback)
