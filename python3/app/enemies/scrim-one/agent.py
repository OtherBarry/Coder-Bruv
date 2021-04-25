import asyncio
import os

import networkx as nx

from app.server_connection import ServerConnection
from app.utilities import PriorityQueue

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
        weight = self.map.graph.nodes[node]["weight"]
        if node in self.danger_nodes:
            weight += 0.1
        return weight

    def _get_edge_weight(self, start, end, properties):
        return self._get_node_weight(start) + self._get_node_weight(end)

    def _get_path_to_best(self, value_func, travel_threshold=10000):
        best_nodes = PriorityQueue()
        for node, data in self.map.graph.nodes(data=True):
            node_value = value_func(node)
            if node_value < value_func(self.us.coords) and node in self.paths:
                best_nodes.push((node_value, self.distances[node], node))

        while not best_nodes.is_empty():
            current_best = best_nodes.pop()[2]
            current_best_path = self.paths[current_best]
            worst_node = max(self._get_node_weight(x) for x in current_best_path)
            if worst_node < travel_threshold:
                return current_best_path

    def find_danger_nodes(self):
        to_visit = list(nx.articulation_points(self.map.graph))
        danger_nodes = set()
        while to_visit:
            current = to_visit.pop()
            if current in danger_nodes:
                continue
            children = self.map.graph[current]
            if len(children) <= 2:
                danger_nodes.add(current)
                to_visit.extend(children)
        for node in self.map.graph.nodes:
            if len(self.map.graph[node]) == 1:
                danger_nodes.add(node)
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
            neighbours = list(self.map.graph[current])
            if len(neighbours) > 2:
                return current
            to_visit.extend(neighbours)
            visited.append(current)

    def is_enemy_trapped(self, cutoff=101):
        if self.us.ammo > 0 and self.them.coords in self.danger_nodes:
            entrance = self.find_danger_entrance(self.them.coords)
            path = self.paths.get(self.them.coords)
            if path is None:
                return None, False
            path = self.paths[self.them.coords]
            if entrance not in path:
                return None, False
            guaranteed_roast = path.index(entrance) >= len(path) // 2
            worst = max(self._get_node_weight(x) for x in path)
            if worst < cutoff:
                return self.paths[entrance], guaranteed_roast
        return None, False

    async def _on_game_tick(self, tick_number, game_state):
        if game_state is not self.state:
            self.state = game_state
            self.map = game_state.map
            self.us = game_state.us
            self.them = game_state.them

        self.danger_nodes = self.find_danger_nodes()

        if self.us.coords not in self.map.graph:
            visitable = []
            for i, m in [(1, 1), (0, 1), (1, -1), (0, -1)]:
                new = list(self.us.coords)
                new[i] += m
                new = tuple(new)
                if new in self.map.graph:
                    visitable.append(new)
            best = min(visitable, key=lambda x: self._get_node_weight(x))
            move = _get_direction_from_coords(self.us.coords, best)
            await self._server.send_move(move)
            return

        self.distances, self.paths = nx.single_source_dijkstra(
            self.map.graph, self.us.coords, weight=self._get_edge_weight
        )

        path, guaranteed = self.is_enemy_trapped()
        if path is not None and len(path) <= 1:
            await self._server.send_bomb()
            return
        elif path is None or not guaranteed:
            best_path = self._get_path_to_best(self._get_node_weight)
            if best_path is not None:
                path = best_path
        if path is None:
            path = self._get_path_to_best(_manhattan_to_centre, 101)
        if path is not None and len(path) > 1:
            move = _get_direction_from_coords(self.us.coords, path[1])
            await self._server.send_move(move)


if __name__ == "__main__":
    Agent()
