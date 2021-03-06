import json
from unittest import TestCase
from unittest.mock import call, patch

from app.state.game_state import GameState


def generate_default_state():
    with open("tests/data/default_state.json") as f:
        return json.load(f)


@patch("app.state.game_state.Map")
@patch("app.state.game_state.Player")  # Note applied bottom up
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
        player_mock.assert_has_calls(
            [call(s) for s in default_state["agent_state"].values()], any_order=True
        )
        self.assertCountEqual(
            default_state["agent_state"].keys(), self.gs.agents.keys()
        )

    def test_set_state_map_correct(self, player_mock, map_mock):
        default_state = generate_default_state()
        self.gs.set_state(default_state)
        map_mock.assert_called_once_with(
            default_state["world"], default_state["entities"]
        )

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
        with open("tests/data/agent_events.json") as f:
            events = json.load(f)
        self.gs.receive_events(events)
        for event in events:
            self.gs.agents[str(event["agent_number"])].handle_action.assert_any_call(
                event["data"]
            )

    def test_update_from_event_agent_state(self, player_mock, map_mock):
        default_state = generate_default_state()
        self.gs.set_state(default_state)
        for state in default_state["agent_state"].values():
            with self.subTest(state=state):
                self.gs.receive_events([{"type": "agent_state", "data": state}])
                self.gs.agents[
                    str(state["number"])
                ].update_state.assert_called_once_with(state, 0)
                self.gs.agents[str(state["number"])].reset_mock()

    def test_update_from_event_entity_spawned(self, player_mock, map_mock):
        self.gs.set_state(generate_default_state())
        with open("tests/data/entities.json") as f:
            entities = json.load(f)
        for entity in entities:
            with self.subTest(entity=entity):
                self.gs.receive_events([{"type": "entity_spawned", "data": entity}])
                self.gs.map.add_entity.assert_called_once_with(entity)
                self.gs.map.reset_mock()

    def test_update_from_event_entity_expired(self, player_mock, map_mock):
        self.gs.set_state(generate_default_state())
        with open("tests/data/entities.json") as f:
            entities = json.load(f)
        for entity in entities:
            with self.subTest(entity=entity):
                coords = [entity["x"], entity["y"]]
                self.gs.receive_events([{"type": "entity_expired", "data": coords}])
                self.gs.map.remove_entity.assert_called_once_with(
                    (entity["x"], entity["y"])
                )
                self.gs.map.reset_mock()
