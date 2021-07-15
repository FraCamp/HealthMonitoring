import json

import connexion
import swagger_server.controllers.rabbitMQ_client as rabbitMQ_client
import six
from flask import Response

from swagger_server.models.config import Config  # noqa: E501
from swagger_server import util


def get_configuration():  # noqa: E501
    """get_configuration

     # noqa: E501


    :rtype: None
    """
    config = rabbitMQ_client.get_configuration()
    if config is not None:
        return Response(
            json.dumps(config),
            status=200
        )
    return Response(
        status=500
    )

# {
#   "threshold": 0,
#   "ping-retries": 0,
#   "monitoring-period": 0
# }

def update_configuration(body):  # noqa: E501
    """update_configuration

     # noqa: E501

    :param body: 
    :type body: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        body = Config.from_dict(connexion.request.get_json())  # noqa: E501
        threshold = body.threshold
        ping_retries = body.ping_retries
        monitoring_period = body.monitoring_period
        if threshold is not None:
            rabbitMQ_client.set_threshold(threshold)
        if ping_retries is not None:
            rabbitMQ_client.set_ping_retries(ping_retries)
        if monitoring_period is not None:
            rabbitMQ_client.set_monitoring_period(monitoring_period)
    return Response(
        status=200
    )
