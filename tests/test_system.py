from app.bot.server_connection import ServerConnection
from unittest import IsolatedAsyncioTestCase
from jsonschema import validate
import copy
import json


def copy_object(data):
    return copy.deepcopy(data)


def create_mock_tick_packet(tick_number, events):
    return{"type": "tick", "payload": {
        "tick": tick_number, "events": copy_object(events)}}


mock_state = {"agent_state": {"0": {"coordinates": [6, 7], "hp": 3, "inventory": {"bombs": 3}, "blast_diameter": 3, "number": 0, "invulnerability": 0}, "1": {"coordinates": [6, 6], "hp": 3, "inventory": {"bombs": 3}, "blast_diameter": 3, "number": 1, "invulnerability": 0}}, "entities": [{"x": 8, "y": 4, "type": "m"}, {"x": 2, "y": 5, "type": "m"}, {"x": 2, "y": 6, "type": "m"}, {"x": 2, "y": 7, "type": "m"}, {"x": 1, "y": 5, "type": "m"}, {"x": 6, "y": 8, "type": "m"}, {"x": 4, "y": 4, "type": "m"}, {"x": 8, "y": 6, "type": "m"}, {"x": 3, "y": 3, "type": "m"}, {"x": 0, "y": 5, "type": "m"}, {"x": 8, "y": 2, "type": "m"}, {"x": 1, "y": 8, "type": "m"}, {"x": 2, "y": 2, "type": "m"}, {"x": 5, "y": 6, "type": "m"}, {"x": 3, "y": 0, "type": "m"}, {"x": 2, "y": 8, "type": "m"}, {"x": 8, "y": 1, "type": "m"}, {
    "x": 6, "y": 2, "type": "w"}, {"x": 2, "y": 3, "type": "w"}, {"x": 3, "y": 5, "type": "w"}, {"x": 7, "y": 6, "type": "w"}, {"x": 4, "y": 3, "type": "w"}, {"x": 0, "y": 3, "type": "w"}, {"x": 5, "y": 3, "type": "w"}, {"x": 3, "y": 2, "type": "w"}, {"x": 5, "y": 5, "type": "w"}, {"x": 8, "y": 7, "type": "w"}, {"x": 3, "y": 7, "type": "w"}, {"x": 1, "y": 7, "type": "w"}, {"x": 4, "y": 0, "type": "w"}, {"x": 3, "y": 6, "type": "w"}, {"x": 0, "y": 0, "type": "w"}, {"x": 7, "y": 5, "type": "w"}, {"x": 3, "y": 4, "type": "w"}, {"x": 0, "y": 8, "type": "w"}, {"x": 8, "y": 3, "type": "w"}, {"x": 6, "y": 0, "type": "w"}, {"x": 1, "y": 4, "type": "o"}, {"x": 0, "y": 4, "type": "o"}, {"x": 3, "y": 8, "type": "o"}, {"x": 0, "y": 2, "type": "o"}, {"x": 4, "y": 7, "type": "o"}], "world": {"width": 9, "height": 9}, "connection": {"id": 7, "role": "agent", "agent_number": 0},
    "tick": 0,
    "config": {
    "tick_rate_hz": 20,
    "game_duration_ticks": 10,
    "fire_spawn_interval_ticks": 5
}}


mock_state_packet = {"type": "game_state",
                     "payload": copy_object(mock_state)}


mock_tick_spawn_packet = create_mock_tick_packet(1, [
    {"type": "entity_spawned", "data": {"x": 5, "y": 4, "type": "a", "expires": 73}}])


mock_tick_expired_packet = create_mock_tick_packet(1, [
    {"type": "entity_expired", "data": [5, 4]}])

mock_agent_state_payload = {"coordinates": [6, 7], "hp": 3, "inventory": {
    "bombs": 2}, "blast_diameter": 3, "number": 0, "invulnerability": 0}

mock_tick_agent_state_packet = create_mock_tick_packet(1, [{"type": "agent_state",
                                                            "data": mock_agent_state_payload}])


mock_tick_agent_action_packet = create_mock_tick_packet(
    1, [{"type": "agent", "data": [0, {"type": "move", "move": "left"}]}])


class TestGameState(IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = ServerConnection("")
        self.maxDiff = None

    def assert_object_equal(self, first, second):
        j1 = json.dumps(first, sort_keys=True, indent=4)
        j2 = json.dumps(second, sort_keys=True, indent=4)
        self.assertEqual(j1, j2)

    def test_mocks_are_valid_with_latest_schema(self):
        with open('data/validation.schema.json') as f:
            schema = json.load(f)
        validate(instance=mock_state_packet, schema=schema.get(
            "definitions").get("ValidServerPacket"))

        validate(instance=mock_tick_spawn_packet, schema=schema.get(
            "definitions").get("ValidServerPacket"))

        validate(instance=mock_tick_agent_action_packet, schema=schema.get(
            "definitions").get("ValidServerPacket"))

        validate(instance=mock_tick_agent_state_packet, schema=schema.get(
            "definitions").get("ValidServerPacket"))

    async def test_on_game_state_payload(self):
        await self.client._on_data(mock_state_packet)
        self.assertEqual((6, 7), self.client._state.agents["0"].coords)
        # TODO: More assertions

    async def test_on_game_entity_spawn_packet(self):
        await self.client._on_data(copy_object(mock_state_packet))
        await self.client._on_data(copy_object(mock_tick_spawn_packet))
        self.assertIn((5, 4), self.client._state.map.graph)
        self.assertEqual("a", self.client._state.map.graph.nodes[(5, 4)]["entity"])

    async def test_on_game_entity_expired_packet(self):
        await self.client._on_data(copy_object(mock_state_packet))
        await self.client._on_data(copy_object(mock_tick_spawn_packet))
        await self.client._on_data(copy_object(mock_tick_expired_packet))
        self.assertIn((5, 4), self.client._state.map.graph)
        self.assertEqual(0, self.client._state.map.graph.nodes[(5, 4)]["weight"])
        self.assertIsNone(self.client._state.map.graph.nodes[(5, 4)].get("entity"))

    async def test_on_agent_state_packet(self):
        await self.client._on_data(copy_object(mock_state_packet))
        await self.client._on_data(copy_object(mock_tick_agent_state_packet))
        self.assertEqual(2, self.client._state.agents["0"].ammo)

    async def test_on_agent_move_packet(self):
        await self.client._on_data(mock_state_packet)
        await self.client._on_data(mock_tick_agent_action_packet)
        self.assertEqual((5, 7), self.client._state.agents["0"].coords)
