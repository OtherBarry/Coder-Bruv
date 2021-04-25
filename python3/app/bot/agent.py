import asyncio
import os
import networkx as nx

from ..utilities import PriorityQueue
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


def _manhattan_to_centre(start_node):
    return abs(4 - start_node[0]) + abs(4 - start_node[1])


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

    def _get_node_weight(self, node):
        return self.map.graph.nodes[node]["weight"]

    def _get_edge_weight(self, start, end, properties):
        return self._get_node_weight(start) + self._get_node_weight(end)

    def _get_path_to_best(self, value_func, travel_threshold=10000):
        best_nodes = PriorityQueue()
        for node, data in self.map.graph.nodes(data=True):
            node_value = value_func(node)
            if node_value < value_func(self.us.coords) and node in self.paths:
                best_nodes.push((node_value, self.distances[node], node))

        while not best_nodes.is_empty():
            current_best = best_nodes.pop()[2]  # For the lowest weight node
            current_best_path = self.paths[
                current_best
            ]
            worst_node = max(self._get_node_weight(x) for x in current_best_path)
            if (worst_node < travel_threshold):
                return current_best_path

        # print("No paths found", end=" | ")

    async def _on_game_tick(self, tick_number, game_state):
        if game_state is not self.state:
            self.state = game_state
            self.map = game_state.map
            self.us = game_state.us
            self.them = game_state.them

        self.distances, self.paths = nx.single_source_dijkstra(
            self.map.graph, self.us.coords, weight=self._get_edge_weight
        )  # Get best paths to all nodes

        path = self._get_path_to_best(self._get_node_weight)
        if path is None:
            path = self._get_path_to_best(_manhattan_to_centre, 101)
        if path is not None and len(path) > 1:
            move = _get_direction_from_coords(self.us.coords, path[1])
            await self._server.send_move(move)
            return
