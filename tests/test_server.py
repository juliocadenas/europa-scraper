import unittest
import socket
import time
import json
from threading import Thread

from server.main import app, broadcast_presence

class TestServer(unittest.TestCase):

    def test_broadcast_presence(self):
        # Test that the broadcast message is sent correctly
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', 6000))
            sock.settimeout(1)

            broadcast_thread = Thread(target=broadcast_presence, daemon=True)
            broadcast_thread.start()

            try:
                data, _ = sock.recvfrom(1024)
                message = data.decode('utf-8')
                self.assertTrue(message.startswith("EUROPA_SCRAPER_SERVER"))
            except socket.timeout:
                self.fail("Broadcast message not received")

if __name__ == '__main__':
    unittest.main()