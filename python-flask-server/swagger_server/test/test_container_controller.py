# coding: utf-8

from __future__ import absolute_import

from swagger_server.test import BaseTestCase


class TestContainerController(BaseTestCase):
    """ContainerController integration test stubs"""

    def test_add_container(self):
        """Test case for add_container

        
        """
        response = self.client.open(
            '/container/{name}'.format(name='name_example'),
            method='POST')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_containers_list(self):
        """Test case for get_containers_list

        
        """
        response = self.client.open(
            '/container',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_monitored_containers_status(self):
        """Test case for get_monitored_containers_status

        
        """
        response = self.client.open(
            '/container/status',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_remove_container(self):
        """Test case for remove_container

        
        """
        response = self.client.open(
            '/container/{name}'.format(name='name_example'),
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
