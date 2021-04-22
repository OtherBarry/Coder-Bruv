import asyncio
import os

from server_connection import ServerConnection

uri = (
    os.environ.get("GAME_CONNECTION_STRING")
    or "ws://127.0.0.1:3000/?role=agent&agentId=agentId&name=defaultName"
)


class Agent:
    def __init__(self):
        self._server = ServerConnection(uri)
        self._server.set_game_tick_callback(self._on_game_tick)

        loop = asyncio.get_event_loop()
        connection = loop.run_until_complete(self._server.connect())
        tasks = [
            asyncio.ensure_future(self._server.handle_messages(connection)),
        ]
        loop.run_until_complete(asyncio.wait(tasks))

    async def _on_game_tick(self, tick_number, game_state):
        # move: self._server.send_move(direction) - can be "up", "down", "left" or "right"
        # bomb: self._server.send_bomb()
        # detonate: self._server.send_detonate(x, y)

        # Game states
        #    Farm: (If no ammo, or disconnected from enemy) Get all ammo and powerups
        #    Kill: Place bombs at articulation points if enemy on other side
        pass


if __name__ == "__main__":
    Agent()
