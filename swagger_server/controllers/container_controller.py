import connexion
import six
from flask import Response
import rabbitMQ_client

from swagger_server.models.container import Container  # noqa: E501
from swagger_server import util


def add_container(name):  # noqa: E501
    """add_container

     # noqa: E501

    :param name: 
    :type name: str

    :rtype: None
    """
    splitted = name.split("/", 2)
    if len(splitted) != 2:
        return Response(
            status=400
        )
    hostname = splitted[0]
    container = splitted[1]
    rabbitMQ_client.add_container(container, hostname)
    return Response(
        status=200
    )


def get_containers_list():  # noqa: E501
    """get_containers_list

     # noqa: E501


    :rtype: List[Container]
    """
    return 'do some magic!'


def get_monitored_containers_status():  # noqa: E501
    """get_monitored_containers_status

     # noqa: E501


    :rtype: List[Container]
    """
    return 'do some magic!'


def remove_container(name):  # noqa: E501
    """remove_container

     # noqa: E501

    :param name: 
    :type name: str

    :rtype: None
    """
    splitted = name.split("/", 2)
    if len(splitted) != 2:
        return Response(
            status=400
        )
    hostname = splitted[0]
    container = splitted[1]
    rabbitMQ_client.remove_container(container, hostname)
    return Response(
        status=200
    )
