import json

import connexion
import swagger_server.controllers.rabbitMQ_manager as rabbitMQ_manager
from flask import Response

from swagger_server.models.config import Config  # noqa: E501


def get_configuration() -> Response:  # noqa: E501
    """
    REST controller method that is triggered by a request for the agent's configurations.
    It returns to the client a list of dictionaries with the following form:

    {
        "hostname": "name"
        "threshold": 50.0,
        "ping-retries": 2,
        "monitoring-period": 4
    }
    """
    config = rabbitMQ_manager.get_configuration()
    if config is not None:
        return Response(
            json.dumps(config),
            status=200
        )
    return Response(
        status=500
    )


def update_configuration(body) -> Response:  # noqa: E501
    """
    REST controller method that is triggered by a request to update the agent's configurations.
    It accepts as parameter a dictionary with the following form:

    {
        "threshold": 50.0,
        "ping-retries": 2,
        "monitoring-period": 4
    }

    None of the dictionary entries is mandatory.
    """
    if connexion.request.is_json:
        body = Config.from_dict(connexion.request.get_json())  # noqa: E501
        threshold = body.threshold
        ping_retries = body.ping_retries
        monitoring_period = body.monitoring_period

        # we send to the rabbitMQ manager a request for each parameter that must be changed so that
        # the request will be forwarded to the whole cluster.
        if threshold is not None:
            rabbitMQ_manager.set_threshold(threshold)
        if ping_retries is not None:
            rabbitMQ_manager.set_ping_retries(ping_retries)
        if monitoring_period is not None:
            rabbitMQ_manager.set_monitoring_period(monitoring_period)
    return Response(
        status=200
    )
