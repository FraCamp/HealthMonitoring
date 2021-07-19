import json

from flask import Response
import swagger_server.controllers.rabbitMQ_manager as rabbitMQ_manager

from swagger_server.models.container import Container  # noqa: E501


def add_container(name):  # noqa: E501
    """
    REST controller method that is triggered by a request to add a container.
    It forwards the request to the cluster.

    :param name: the name of the container to add, containing the hostname.
    :type name: str
    """
    # We check if the name is in the correct format: it must contain the hostname, followed by
    # a dash (-) followed by the container name.
    split = name.split("-", 2)
    if len(split) != 2:
        return Response(
            status=400
        )
    hostname = split[0]
    container = split[1]
    rabbitMQ_manager.add_container(container, hostname)
    return Response(
        status=200
    )


def get_containers_list():  # noqa: E501
    """get_containers_list

    REST controller method that is triggered by a request for the list of containers.
    It forwards the request to the cluster and returns the result.

    :rtype: List[str]
    """
    result = rabbitMQ_manager.get_containers_list()
    if result is None:
        return Response(
            status=500
        )
    else:
        return Response(
            json.dumps(result),
            status=200
        )


def get_monitored_containers_status():  # noqa: E501
    """

    REST controller method that is triggered by a request for the status of all containers.
    It forwards the request to the cluster and returns the result.

    :rtype: List[Container]
    """
    result = rabbitMQ_manager.get_container_status()
    if result is None:
        return Response(
            status=500
        )
    else:
        return Response(
            json.dumps(result),
            status=200
        )


def get_monitored_container_status(name):  # noqa: E501
    """get_monitored_container_status

    REST controller method that is triggered by a request for the status of one container.
    It forwards the request to the cluster and returns the result.

    :param name: the name of the container of interest
    :type name: str

    :rtype: Container
    """
    # We check if the name is in the correct format: it must contain the hostname, followed by
    # a dash (-) followed by the container name.
    split = name.split("-", 2)
    if len(split) != 2:
        return Response(
            status=400
        )
    hostname = split[0]
    container = split[1]

    result = rabbitMQ_manager.get_container_status(container, hostname)
    if result is None:
        return Response(
            status=404
        )
    return Response(
        json.dumps(result),
        status=200
    )


def remove_container(name):  # noqa: E501
    """
    REST controller method that is triggered by a request to remove a container.
    It forwards the request to the cluster.

    :param name: the name of the container to remove, containing the hostname.
    :type name: str
    """
    # We check if the name is in the correct format: it must contain the hostname, followed by
    # a dash (-) followed by the container name.
    split = name.split("-", 2)
    if len(split) != 2:
        return Response(
            status=400
        )
    hostname = split[0]
    container = split[1]

    rabbitMQ_manager.remove_container(container, hostname)
    return Response(
        status=200
    )
