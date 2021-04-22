from game_state import GameState
import asyncio
import os

uri = (
    os.environ.get("GAME_CONNECTION_STRING")
    or "ws://127.0.0.1:3000/?role=agent&agentId=agentId&name=defaultName"
)


class Agent:
    def __init__(self):
        self._client = GameState(uri)

        self._client.set_game_tick_callback(self._on_game_tick)
        loop = asyncio.get_event_loop()
        connection = loop.run_until_complete(self._client.connect())
        tasks = [
            asyncio.ensure_future(self._client.handle_messages(connection)),
        ]
        loop.run_until_complete(asyncio.wait(tasks))

    async def _on_game_tick(self, tick_number, game_state):
        # move: self._client.send_move(direction) - can be "up", "down", "left" or "right"
        # bomb: self._client.send_bomb()
        # detonate: self._client.send_detonate(x, y)
        pass


if __name__ == "__main__":
    Agent()
