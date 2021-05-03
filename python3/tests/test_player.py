import json
from unittest import TestCase
from unittest.mock import patch

from app.state.player import Player


def get_default_state(agent_id="0"):
    with open("tests/data/default_state.json") as f:
        state = json.load(f)
    return state["agent_state"][agent_id]


class TestPlayer(TestCase):
    def assertPlayerStateEquals(self, player, state):
        self.assertEqual(player.id, str(state["number"]))
        self.assertEqual(
            player.coords, (state["coordinates"][0], state["coordinates"][1])
        )
        self.assertEqual(player.hp, state["hp"])
        self.assertEqual(player.ammo, state["inventory"]["bombs"])
        self.assertEqual(player.blast_diameter, state["blast_diameter"])
        self.assertEqual(player._invulnerable_until, state["invulnerability"])

    @patch("app.state.player.Player.update_state", autospec=True)
    def test_constructor_calls_update_state(self, mocked):
        state = get_default_state()
        player = Player(state)
        mocked.assert_called_once_with(player, state, 0)

    def test_handle_action_non_move(self):
        with open("tests/data/agent_events.json") as f:
            events = json.load(f)
        state = get_default_state()
        player = Player(state)
        for event in events:
            event = event["data"]
            if event["type"] != "move":
                with self.subTest(event=event):
                    player.handle_action(event)
                    self.assertPlayerStateEquals(player, state)

    def test_move_up(self):
        state = get_default_state()
        player = Player(state)
        player.coords = (1, 1)
        player.handle_action({"type": "move", "move": "up"})
        self.assertEqual((1, 2), player.coords)

    def test_move_down(self):
        state = get_default_state()
        player = Player(state)
        player.coords = (1, 1)
        player.handle_action({"type": "move", "move": "down"})
        self.assertEqual((1, 0), player.coords)

    def test_move_left(self):
        state = get_default_state()
        player = Player(state)
        player.coords = (1, 1)
        player.handle_action({"type": "move", "move": "left"})
        self.assertEqual((0, 1), player.coords)

    def test_move_right(self):
        state = get_default_state()
        player = Player(state)
        player.coords = (1, 1)
        player.handle_action({"type": "move", "move": "right"})
        self.assertEqual((2, 1), player.coords)
