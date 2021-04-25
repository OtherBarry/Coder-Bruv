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
        self.danger_nodes = self.find_danger_nodes()

        path, guaranteed = self.is_enemy_trapped()
        if path is not None and guaranteed:
            if len(path) <= 1:
                await self._server.send_bomb()
                return
        else:
            best_path = self._get_path_to_best(self._get_node_weight)
            if best_path is not None:
                path = best_path
        if path is None:
            path = self._get_path_to_best(_manhattan_to_centre, 101)
        if path is not None and len(path) > 1:
            move = _get_direction_from_coords(self.us.coords, path[1])
            await self._server.send_move(move)
            return

    def find_danger_nodes(graph):
        to_visit = list(nx.articulation_points(graph))
        danger_nodes = set()
        while to_visit:
            current = to_visit.pop()
            if current in danger_nodes:
                continue
            children = graph[current]
            if len(children) <= 2:
                danger_nodes.add(current)
                to_visit.extend(children)
        return danger_nodes

    def find_danger_entrance(self, coord):
        if coord not in self.danger_nodes:
            return None
        to_visit = [coord]
        visited = []
        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            neighbours = list(self.map.graph.neighbours(current))
            if len(neighbours) > 2:
                return current
            to_visit.extend(neighbours)
            visited.append(current)

    def is_enemy_trapped(self):
        if self.them in self.find_danger_nodes():
            entrance = self.find_danger_entrance(self.them.coords)
            path = self.paths[self.them.coords]
            guaranteed_roast = path.index(entrance) >= len(path) // 2
            return self.paths[entrance], guaranteed_roast
        return None, False