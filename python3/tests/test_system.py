import json
from unittest import IsolatedAsyncioTestCase

from jsonschema import validate

from app.server_connection import ServerConnection


class TestGameState(IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = ServerConnection("")
        self.maxDiff = None
        with open('tests/data/validation.schema.json') as f:
            self.schema = json.load(f)

    def get_server_packet(self, name):
        with open("tests/data/server_packets/" + name + ".json") as f:
            packet = json.load(f)
            print(packet)
        validate(packet, self.schema["definitions"]["ValidServerPacket"])
        return packet

    async def test_on_game_state_payload(self):
        await self.client._on_data(self.get_server_packet("game_state"))
        self.assertEqual((6, 7), self.client._state.agents["0"].coords)
        # TODO: More assertions

    async def test_on_game_entity_spawn_packet(self):
        await self.client._on_data(self.get_server_packet("game_state"))
        await self.client._on_data(self.get_server_packet("tick_entity_spawned"))
        self.assertIn((5, 4), self.client._state.map.graph)
        self.assertEqual("a", self.client._state.map.graph.nodes[(5, 4)]["entity"])

    async def test_on_game_entity_expired_packet(self):
        await self.client._on_data(self.get_server_packet("game_state"))
        await self.client._on_data(self.get_server_packet("tick_entity_spawned"))
        await self.client._on_data(self.get_server_packet("tick_entity_expired"))
        self.assertIn((5, 4), self.client._state.map.graph)
        self.assertEqual(100, self.client._state.map.graph.nodes[(5, 4)]["weight"])
        self.assertIsNone(self.client._state.map.graph.nodes[(5, 4)].get("entity"))

    async def test_on_agent_state_packet(self):
        await self.client._on_data(self.get_server_packet("game_state"))
        await self.client._on_data(self.get_server_packet("tick_agent_state"))
        self.assertEqual(2, self.client._state.agents["0"].ammo)

    async def test_on_agent_move_packet(self):
        await self.client._on_data(self.get_server_packet("game_state"))
        await self.client._on_data(self.get_server_packet("tick_agent_action"))
        self.assertEqual((5, 6), self.client._state.agents["1"].coords)
