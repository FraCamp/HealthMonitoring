# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class Container(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, name: str=None, monitored: bool=None, running: bool=None, started_at: str=None, restart_count: int=None, image: str=None, ip: str=None, packet_loss: str=None):  # noqa: E501
        """Container - a model defined in Swagger

        :param name: The name of this Container.  # noqa: E501
        :type name: str
        :param monitored: The monitored of this Container.  # noqa: E501
        :type monitored: bool
        :param running: The running of this Container.  # noqa: E501
        :type running: bool
        :param started_at: The started_at of this Container.  # noqa: E501
        :type started_at: str
        :param restart_count: The restart_count of this Container.  # noqa: E501
        :type restart_count: int
        :param image: The image of this Container.  # noqa: E501
        :type image: str
        :param ip: The ip of this Container.  # noqa: E501
        :type ip: str
        :param packet_loss: The packet_loss of this Container.  # noqa: E501
        :type packet_loss: str
        """
        self.swagger_types = {
            'name': str,
            'monitored': bool,
            'running': bool,
            'started_at': str,
            'restart_count': int,
            'image': str,
            'ip': str,
            'packet_loss': str
        }

        self.attribute_map = {
            'name': 'name',
            'monitored': 'monitored',
            'running': 'running',
            'started_at': 'started_at',
            'restart_count': 'restart_count',
            'image': 'image',
            'ip': 'ip',
            'packet_loss': 'packet-loss'
        }

        self._name = name
        self._monitored = monitored
        self._running = running
        self._started_at = started_at
        self._restart_count = restart_count
        self._image = image
        self._ip = ip
        self._packet_loss = packet_loss

    @classmethod
    def from_dict(cls, dikt) -> 'Container':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Container of this Container.  # noqa: E501
        :rtype: Container
        """
        return util.deserialize_model(dikt, cls)

    @property
    def name(self) -> str:
        """Gets the name of this Container.


        :return: The name of this Container.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name: str):
        """Sets the name of this Container.


        :param name: The name of this Container.
        :type name: str
        """
        if name is None:
            raise ValueError("Invalid value for `name`, must not be `None`")  # noqa: E501

        self._name = name

    @property
    def monitored(self) -> bool:
        """Gets the monitored of this Container.


        :return: The monitored of this Container.
        :rtype: bool
        """
        return self._monitored

    @monitored.setter
    def monitored(self, monitored: bool):
        """Sets the monitored of this Container.


        :param monitored: The monitored of this Container.
        :type monitored: bool
        """

        self._monitored = monitored

    @property
    def running(self) -> bool:
        """Gets the running of this Container.


        :return: The running of this Container.
        :rtype: bool
        """
        return self._running

    @running.setter
    def running(self, running: bool):
        """Sets the running of this Container.


        :param running: The running of this Container.
        :type running: bool
        """

        self._running = running

    @property
    def started_at(self) -> str:
        """Gets the started_at of this Container.


        :return: The started_at of this Container.
        :rtype: str
        """
        return self._started_at

    @started_at.setter
    def started_at(self, started_at: str):
        """Sets the started_at of this Container.


        :param started_at: The started_at of this Container.
        :type started_at: str
        """

        self._started_at = started_at

    @property
    def restart_count(self) -> int:
        """Gets the restart_count of this Container.


        :return: The restart_count of this Container.
        :rtype: int
        """
        return self._restart_count

    @restart_count.setter
    def restart_count(self, restart_count: int):
        """Sets the restart_count of this Container.


        :param restart_count: The restart_count of this Container.
        :type restart_count: int
        """

        self._restart_count = restart_count

    @property
    def image(self) -> str:
        """Gets the image of this Container.


        :return: The image of this Container.
        :rtype: str
        """
        return self._image

    @image.setter
    def image(self, image: str):
        """Sets the image of this Container.


        :param image: The image of this Container.
        :type image: str
        """

        self._image = image

    @property
    def ip(self) -> str:
        """Gets the ip of this Container.


        :return: The ip of this Container.
        :rtype: str
        """
        return self._ip

    @ip.setter
    def ip(self, ip: str):
        """Sets the ip of this Container.


        :param ip: The ip of this Container.
        :type ip: str
        """

        self._ip = ip

    @property
    def packet_loss(self) -> str:
        """Gets the packet_loss of this Container.


        :return: The packet_loss of this Container.
        :rtype: str
        """
        return self._packet_loss

    @packet_loss.setter
    def packet_loss(self, packet_loss: str):
        """Sets the packet_loss of this Container.


        :param packet_loss: The packet_loss of this Container.
        :type packet_loss: str
        """

        self._packet_loss = packet_loss