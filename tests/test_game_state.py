import json
from unittest import TestCase
from unittest.mock import call, patch

from bot.game_state import GameState


def generate_default_state():
    with open("default_state.json") as f:
        return json.load(f)


@patch("bot.game_state.Map", autospec=True)
@patch("bot.game_state.Player", autospec=True)
class TestGameState(TestCase):
    def setUp(self):
        self.gs = GameState()

    def test_set_state_tick_correct(self, player_mock, map_mock):
        default_state = generate_default_state()
        self.gs.set_state(default_state)
        self.assertEqual(default_state["tick"], self.gs.tick)

    def test_set_state_desync_correct(self, player_mock, map_mock):
        self.gs.set_state(generate_default_state())
        self.assertFalse(self.gs.desynced)

    def test_set_state_agents_correct(self, player_mock, map_mock):
        default_state = generate_default_state()
        self.gs.set_state(default_state)
        player_mock.assert_has_calls([call(s) for s in default_state["agent_state"].values()], any_order=True)
        self.assertCountEqual(default_state["agent_state"].keys(), self.gs.agents.keys())
        for agent in self.gs.agents.values():
            self.assertIsInstance(agent, player_mock.__class__)

    def test_set_state_map_correct(self, player_mock, map_mock):
        default_state = generate_default_state()
        self.gs.set_state(default_state)
        map_mock.assert_called_once_with(default_state["world"], default_state["entities"], self.gs.agents)

    def test_update_tick_matches(self, player_mock, map_mock):
        self.gs.set_state(generate_default_state())
        self.assertFalse(self.gs.desynced)
        self.gs.update_tick(1)
        self.assertFalse(self.gs.desynced)
        self.assertEqual(1, self.gs.tick)

    def test_update_tick_behind(self, player_mock, map_mock):
        self.gs.set_state(generate_default_state())
        self.assertFalse(self.gs.desynced)
        self.gs.update_tick(0)
        self.assertTrue(self.gs.desynced)
        self.assertEqual(0, self.gs.tick)

    def test_update_tick_ahead(self, player_mock, map_mock):
        self.gs.set_state(generate_default_state())
        self.assertFalse(self.gs.desynced)
        self.gs.update_tick(2)
        self.assertTrue(self.gs.desynced)
        self.assertEqual(2, self.gs.tick)

    def test_update_from_event_agent(self, player_mock, map_mock):
        self.gs.set_state(generate_default_state())
        with open("agent_events.json") as f:
            events = json.load(f)
        for event in events:
            with self.subTest(event=event):
                self.gs.update_from_event(event)
                agent, data = event["data"]
                self.gs.agents[str(agent)].handle_action.assert_called_once_with(data)
                self.gs.agents[str(agent)].reset_mock()

    def test_update_from_event_agent_state(self, player_mock, map_mock):
        default_state = generate_default_state()
        self.gs.set_state(default_state)
        for state in default_state["agent_state"].values():
            with self.subTest(state=state):
                self.gs.update_from_event({"type": "agent_state", "data": state})
                self.gs.agents[
                    str(state["number"])
                ].update_state.assert_called_once_with(state)
                self.gs.agents[str(state["number"])].reset_mock()

    def test_update_from_event_entity_spawned(self, player_mock, map_mock):
        default_state = generate_default_state()
        self.gs.set_state(default_state)
        for entity in default_state["entities"]:
            with self.subTest(entity=entity):
                self.gs.update_from_event({"type": "entity_spawned", "data": entity})
                self.gs.map.add_entity.assert_called_once_with(entity, self.gs.agents)
                self.gs.map.reset_mock()

    def test_update_from_event_entity_expired(self, player_mock, map_mock):
        default_state = generate_default_state()
        self.gs.set_state(default_state)
        for entity in default_state["entities"]:
            with self.subTest(entity=entity):
                coords = [entity["x"], entity["y"]]
                self.gs.update_from_event({"type": "entity_expired", "data": coords})
                self.gs.map.remove_entity.assert_called_once_with(
                    (entity["x"], entity["y"])
                )
                self.gs.map.reset_mock()
