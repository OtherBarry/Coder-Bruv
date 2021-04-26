import asyncio
import os
import networkx as nx
import math

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

def _manhattan_distance(start, end):
    return abs(end[0] - start[0]) + abs(end[1] - start[1])

def _manhattan_to_centre(start_node):
    return _manhattan_distance(start_node, (4, 4))


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
        if self.us.is_invulnerable:
            weight = min(100, weight)
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
            current_best_path = self.paths[
                current_best
            ]
            worst_node = max(self._get_node_weight(x) for x in current_best_path)
            if worst_node < travel_threshold:
                return current_best_path

    def _find_tunnel_nodes(self, coords):
        visited = [coords]
        to_visit = list(self.map.graph[coords])
        while to_visit:
            current = to_visit.pop()
            visited.append(current)
            neighbours = self.map.graph[current]
            if len(neighbours) <= 2:
                yield current
                to_visit.extend([n for n in neighbours if n not in visited])

    def _find_danger_nodes(self):
        danger_nodes = set()
        for node in self.map.graph.nodes:
            if node not in danger_nodes and len(self.map.graph[node]) == 1:
                danger_nodes.add(node)
                for n in self._find_tunnel_nodes(node):
                    danger_nodes.add(n)
        return danger_nodes

    def _find_danger_entrance(self, coord):
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

    def _is_enemy_trapped(self, cutoff=101):
        if self.us.ammo > 0 and self.them.coords in self.danger_nodes:
            entrance = self._find_danger_entrance(self.them.coords)
            path = self.paths.get(self.them.coords)
            if path is None:
                return None, False
            worst = max(self._get_node_weight(x) for x in path)
            if worst < cutoff:
                guaranteed_roast = len(self.paths[entrance]) <= len(nx.dijkstra_path(self.map.graph, self.them.coords, entrance, self._get_edge_weight))
                return path, guaranteed_roast
        return None, False

    def _generate_neighbouring_tiles(self, coords):
        for i, m in [(1, 1), (0, 1), (1, -1), (0, -1)]:
            new = list(coords)
            new[i] += m
            new = tuple(new)
            if new in self.map.graph:
                yield new

    def _dismount_bomb(self):
        neighbours = []
        distance_to_enemy = _manhattan_distance(self.us.coords, self.them.coords)
        for neighbour in self._generate_neighbouring_tiles(self.us.coords):
            if _manhattan_distance(neighbour, self.them.coords) >= distance_to_enemy:
                neighbours.append(neighbour)
        best_weight = math.inf
        best_nodes = set()
        for neighbour in neighbours:
            distances, paths = nx.single_source_dijkstra(self.map.graph, neighbour, weight=self._get_edge_weight)
            for node in distances:
                mean_weight = distances[node] / len(paths[node])
                if mean_weight < best_weight:
                    best_weight = mean_weight
                    best_nodes = {neighbour, }
                elif mean_weight == best_weight:
                    best_nodes.add(neighbour)
        if len(best_nodes) > 1:
            return max(best_nodes, key=lambda x: len(nx.node_connected_component(self.map.graph, x)))
        for node in best_nodes:
            return node
        for node in self._generate_neighbouring_tiles(self.us.coords):
            return node

    async def _on_game_tick(self, tick_number, game_state):
        if game_state is not self.state:
            self.state = game_state
            self.map = game_state.map
            self.us = game_state.us
            self.them = game_state.them

        # TODO: Avoid Traps
        # TODO: Don't avoid our own bombs until close to det
        # TODO: Improve trapping logic to account for blast radius and both inside
        # TODO: Logic in regards to current ammo/hp
        # TODO: Handle existence of other player
        # TODO: Break out of cages

        self.danger_nodes = self._find_danger_nodes()

        if self.us.coords not in self.map.graph:
            target = self._dismount_bomb()
            move = _get_direction_from_coords(self.us.coords, target)
            await self._server.send_move(move)
            return

        self.distances, self.paths = nx.single_source_dijkstra(
            self.map.graph, self.us.coords, weight=self._get_edge_weight
        )  # Get best paths to all nodes

        path, guaranteed = self._is_enemy_trapped()
        if path is not None and len(path) - 1 <= self.us.blast_diameter // 2:
            await self._server.send_bomb()
            return
        elif not guaranteed:
            best_path = self._get_path_to_best(self._get_node_weight)
            if best_path is not None:
                path = best_path
        if path is None:
            path = self._get_path_to_best(_manhattan_to_centre, 101)
        if path is not None and len(path) > 1:
            move = _get_direction_from_coords(self.us.coords, path[1])
            await self._server.send_move(move)
            return
