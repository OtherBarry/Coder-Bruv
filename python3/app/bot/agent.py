import asyncio
import os
import math
import networkx as nx

from ..server_connection import ServerConnection

uri = (
    os.environ.get("GAME_CONNECTION_STRING")
    or "ws://127.0.0.1:3000/?role=agent&agentId=agentId&name=defaultName"
)


def _get_direction_from_coords(start, end):
    if start[0] > end[0]:
        return "left"
    elif start[0] < end[0]:
        return "right"
    elif start[1] > end[1]:
        return "down"
    elif start[1] < end[1]:
        return "up"
    else:
        raise ValueError


class Agent:
    def __init__(self):
        self._server = ServerConnection(uri)
        self._server.set_game_tick_callback(self._on_game_tick)
        self.state = None

        loop = asyncio.get_event_loop()
        connection = loop.run_until_complete(self._server.connect())
        tasks = [
            asyncio.ensure_future(self._server.handle_messages(connection)),
        ]
        loop.run_until_complete(asyncio.wait(tasks))

    def _get_weight(self, start, end, properties):
        return self.map.graph.nodes[start]["weight"] + self.map.graph.nodes[end]["weight"]

    async def _on_game_tick(self, tick_number, game_state):
        if game_state is not self.state:
            self.state = game_state
            self.map = game_state.map
            self.us = game_state.us
            self.them = game_state.them

        best = sorted(self.map.graph.nodes(data=True), key=lambda x: x[1]["weight"])
        for target, data in best:
            if target != self.us.coords and data["weight"] < self.map.graph.nodes[self.us.coords]["weight"] and nx.has_path(self.map.graph, self.us.coords, target):
                print(target)
                path = nx.shortest_path(self.map.graph, self.us.coords, target, self._get_weight)
                await self._server.send_move(_get_direction_from_coords(self.us.coords, path[1]))
                return

        destination = min(nx.neighbors(self.map.graph, self.us.coords), key=lambda x: self.map.graph.nodes[x]["weight"], default=self.map.graph.nodes[self.us.coords]["weight"])
        await self._server.send_move(_get_direction_from_coords(self.us.coords, destination))
