from unittest import TestCase
from unittest.mock import patch

from app.server_connection import ServerConnection

@patch("app.bot.game_state.GameState", autospec=True)
class TestServerConnection(TestCase):

    def setUp(self):
        self.sc = ServerConnection()
