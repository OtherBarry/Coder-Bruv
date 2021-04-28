import json
import time
import websockets

from .state.game_state import GameState


class ServerConnection:
    VALID_MOVES = ("up", "down", "left", "right")

    def __init__(self, connection_string: str):
        self._connection_string = connection_string
        self._state = GameState()
        self._tick_callback = None

    def set_game_tick_callback(self, generate_agent_action_callback):
        self._tick_callback = generate_agent_action_callback

    async def connect(self):
        self.connection = await websockets.client.connect(self._connection_string)
        if self.connection.open:
            return self.connection

    async def _send(self, packet):
        await self.connection.send(json.dumps(packet))

    async def send_move(self, move: str):
        if move in ServerConnection.VALID_MOVES:
            packet = {"type": "move", "move": move}
            await self._send(packet)

    async def send_bomb(self):
        packet = {"type": "bomb"}
        await self._send(packet)

    async def send_detonate(self, x, y):
        packet = {"type": "detonate", "coordinates": [x, y]}
        await self._send(packet)

    async def handle_messages(self, connection):
        while True:
            try:
                raw_data = await connection.recv()
                data = json.loads(raw_data)
                await self._on_data(data)
            except websockets.exceptions.ConnectionClosed:
                print("Connection with server closed")
                break

    async def _on_data(self, data):
        data_type = data.get("type")
        if data_type == "game_state":
            payload = data.get("payload")
            self._on_game_state(payload)
        elif data_type == "tick":
            payload = data.get("payload")
            self._state.update_tick(payload.get("tick"))
            await self._on_game_tick(payload)
        elif data_type != "info":
            print(f'unknown packet "{data_type}": {data}')

    def _on_game_state(self, game_state):
        self._state.set_state(game_state)

    async def _on_game_tick(self, game_tick):
        start = time.time()
        self._state.receive_events(game_tick.get("events"))
        if self._tick_callback is not None:
            tick_number = game_tick.get("tick")
            await self._tick_callback(tick_number, self._state)
        end = time.time()
        print("TIME: {:.2f}%".format(100 * (end - start) / 0.1))
