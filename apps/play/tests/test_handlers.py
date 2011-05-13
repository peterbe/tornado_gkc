from apps.main.tests.base import BaseHTTPTestCase, TestClient
from utils.http_test_client import TestClient

class HandlersTestCase(BaseHTTPTestCase):
    def test_starting_play(self):
        url = self.reverse_url('start_play')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('login' in response.headers['location'])

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        play_url = self.reverse_url('play')
        self.assertTrue(play_url in response.body)

    def test_play_homepage(self):
        url = self.reverse_url('play')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('login' in response.headers['location'])

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
