import asyncio
import os
import networkx as nx
import math

from ..utilities import Entity, PriorityQueue
from ..server_connection import ServerConnection

uri = (
    os.environ.get("GAME_CONNECTION_STRING")
    or "ws://127.0.0.1:3000/?role=agent&agentId=agentId&name=defaultName"
)
INDEX_MAP = {0: "ATTACKING  ", 1: "IMPROVING  ", 2: "CENTERING  "}


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
        bomb_owners = self.map.bomb_library.get_bomb_impact_owners(node)
        if self.them.id in bomb_owners or None in bomb_owners:
            weight += self.map.WEIGHT_MAP[Entity.BLAST]
        elif self.us.id in bomb_owners:
            weight += 1
        if self.us.is_invulnerable:
            weight = min(110, weight)
        entrance = self.danger_nodes.get(node)
        if node == self.them.coords:
            if self.next_to_enemy:
                weight += math.inf
            elif self.state.tick < 1800:
                weight -= 1
        if entrance is not None:
            us_to_entrance = _manhattan_distance(self.us.coords, entrance)
            them_to_entrance = _manhattan_distance(self.them.coords, entrance)
            if them_to_entrance <= 2 or us_to_entrance >= them_to_entrance:
                weight += 555
        return weight

    def _get_edge_weight(self, start, end, properties):
        return self._get_node_weight(start) + self._get_node_weight(end)

    def _get_path_to_best(self, value_func):
        best_nodes = PriorityQueue()
        for node, data in self.map.graph.nodes(data=True):
            if node == self.us.coords:
                continue
            entrance = self.danger_nodes.get(node)
            if entrance is not None:
                our_path = self.paths[self.us.coords].get(entrance)
                their_path = self.paths[self.them.coords].get(entrance)
                if (
                    our_path is not None
                    and their_path is not None
                    and len(their_path) <= len(our_path)
                ):
                    continue
            node_value = value_func(node)
            if (
                node_value < value_func(self.us.coords)
                and node in self.paths[self.us.coords]
            ):
                best_nodes.push(
                    (node_value, self.distances[self.us.coords][node], node)
                )

        if not best_nodes.is_empty():
            current_best = best_nodes.pop()[2]
            return self.paths[self.us.coords][current_best]
        return None

    def _find_danger_nodes(self):
        danger_nodes = {}
        for node in self.map.graph.nodes:
            if node not in danger_nodes and len(self.map.graph[node]) == 1:
                visited = [node]
                to_visit = list(self.map.graph[node])
                exit = None
                while to_visit:
                    current = to_visit.pop()
                    neighbours = self.map.graph[current]
                    if len(neighbours) > 2:
                        exit = current
                        break
                    visited.append(current)
                    if len(neighbours) <= 2:
                        to_visit.extend([n for n in neighbours if n not in visited])
                for n in visited:
                    danger_nodes[n] = exit
        return danger_nodes

    def _is_enemy_trapped(self):
        entrance = self.danger_nodes.get(self.them.coords)
        if self.us.ammo > 0 and entrance is not None:
            path = self.paths[self.us.coords].get(self.them.coords)
            if path is None:
                return None, False
            us_to_entrance = self.paths[self.us.coords].get(entrance)
            them_to_entrance = self.paths[self.them.coords].get(entrance)
            if us_to_entrance is not None and them_to_entrance is not None:
                guaranteed_roast = len(us_to_entrance) < len(them_to_entrance)
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
        neighbours = list(self._generate_neighbouring_tiles(self.us.coords))
        best = PriorityQueue()
        for neighbour in neighbours:
            distances, paths = nx.single_source_dijkstra(
                self.map.graph, neighbour, weight=self._get_edge_weight
            )
            connected_nodes = nx.node_connected_component(self.map.graph, neighbour)
            for node in distances:
                mean_weight = distances[node] / len(paths[node])
                best.push((mean_weight, -len(connected_nodes), neighbour))
        if neighbours:
            return best.pop()[2]
        return None

    async def _on_game_tick(self, tick_number, game_state):
        if game_state is not self.state:
            self.state = game_state
            self.map = game_state.map
            self.us = game_state.us
            self.them = game_state.them

        # TODO: Break out of cages
        # TODO: Treat fire with same weight as bombs
        # TODO: Handle fire spawning better - We should be able to predict when/where it will spawn
        # TODO: Logic in regards to current ammo/hp

        self.danger_nodes = self._find_danger_nodes()
        self.next_to_enemy = _manhattan_distance(self.us.coords, self.them.coords) == 1

        detonatable_bombs = [
            b
            for b in self.map.bomb_library.get_bombs_impacting(self.them.coords)
            if b.owner == self.us.id
        ]

        # Dismount or chadonate bomb if just planted
        if self.us.coords not in self.map.graph:
            if self.us.hp >= 2 > self.them.hp:
                for bomb in detonatable_bombs:
                    if bomb.position == self.us.coords:
                        await self._server.send_detonate(*bomb.position)
                        print("CHADONATING", end=" | ")
                        return
            print("DISMOUNTING", end=" | ")
            target = self._dismount_bomb()
            if target is not None:
                move = _get_direction_from_coords(self.us.coords, target)
                await self._server.send_move(move)
                return

        # Move to entrance first if both 1 away
        entrance = self.danger_nodes.get(self.them.coords)
        if self.us.ammo > 0 and entrance:
            us_to_entrance = _manhattan_distance(self.us.coords, entrance)
            them_to_entrance = _manhattan_distance(self.them.coords, entrance)
            if (
                us_to_entrance == them_to_entrance == 1
                and self._get_node_weight(entrance) < self.map.WEIGHT_MAP[Entity.BLAST]
            ):
                print("BLOCKING   ", end=" | ")
                move = _get_direction_from_coords(self.us.coords, entrance)
                await self._server.send_move(move)
                return

        # Detonate bomb if bad for enemy
        for bomb in detonatable_bombs:
            if (
                self.us.hp >= 2 > self.them.hp
                or bomb not in self.map.bomb_library.get_bombs_impacting(self.us.coords)
            ):
                await self._server.send_detonate(*bomb.position)
                print("DETONATING ", end=" | ")
                return

        # Plant bomb if abundance of ammo and space and next to enemy
        if (
            self.us.coords not in self.danger_nodes
            and self.next_to_enemy
            and self.us.ammo > self.them.hp
        ):
            print("AREA DENIAL", end=" | ")
            await self._server.send_bomb()
            return

        for bomb in self.map.bomb_library.get_bombs_impacting(self.them.coords):
            if bomb.owner == self.us.id and (
                self.us.hp >= 2 > self.them.hp
                or bomb not in self.map.bomb_library.get_bombs_impacting(self.us.coords)
            ):
                await self._server.send_detonate(*bomb.position)
                print("DETONATING ", end=" | ")
                return

        # Generate dijkstra paths from all players to all other nodes
        self.paths = {}
        self.distances = {}
        for player in [self.us.coords, self.them.coords]:
            if player in self.map.graph:
                self.distances[player], self.paths[player] = nx.single_source_dijkstra(
                    self.map.graph, player, weight=self._get_edge_weight
                )
            else:
                self.distances[player] = {
                    n: 1 for n in self._generate_neighbouring_tiles(player)
                }
                self.paths[player] = {
                    n: [player, n] for n in self._generate_neighbouring_tiles(player)
                }

        attack_path, kill_confirmed = self._is_enemy_trapped()
        if attack_path is not None:
            if self.next_to_enemy:
                # Plant bomb if enemy trapped and we're next to enemy
                print("PLANTING   ", end=" | ")
                await self._server.send_bomb()
                return
            elif (
                kill_confirmed
                and max(self._get_node_weight(node) for node in attack_path)
                < self.map.WEIGHT_MAP[Entity.BLAST]
            ):
                print("ATTACKING  ", end=" | ")
                move = _get_direction_from_coords(self.us.coords, attack_path[1])
                await self._server.send_move(move)
                return
        farm_path = self._get_path_to_best(self._get_node_weight)
        chill_path = self._get_path_to_best(_manhattan_to_centre)
        paths = [attack_path, farm_path, chill_path]
        best_path = None
        for index, path in enumerate(paths):
            if path is not None and len(path) > 1:
                attack = index > 0
                entrance = self.danger_nodes.get(path[1])
                if not attack and entrance is not None:
                    us_to_entrance = self.paths[self.us.coords].get(entrance)
                    them_to_entrance = self.paths[self.them.coords].get(entrance)
                    if (
                        us_to_entrance
                        and them_to_entrance
                        and len(us_to_entrance) <= len(them_to_entrance)
                    ):
                        continue
                path.pop(0)
                worst_node = max(self._get_node_weight(node) for node in path)
                if best_path is None or worst_node < best_path[0]:
                    best_path = (worst_node, index)

        if best_path is not None:
            worst_node, index = best_path
            path = paths[index]
            if worst_node <= self._get_node_weight(self.us.coords) and path:
                print(INDEX_MAP[index], end=" | ")
                # print("\n")
                # print("WORST NODE: ", worst_node)
                # print("ENEMY NODE: ", self.them.coords)
                # print("NEXT NODE: coords ", path[0], "| Danger ", self.danger_nodes.get(path[0]), "| weight", self._get_node_weight(path[0]))
                # print("CURRENT NODE: coords ", self.us.coords, "| Danger ", self.danger_nodes.get(self.us.coords), "| weight", self._get_node_weight(self.us.coords))
                move = _get_direction_from_coords(self.us.coords, path[0])
                await self._server.send_move(move)
                return
        print("WAITING    ", end=" | ")

    def prison_break(self, threshold):
        connected_nodes = nx.node_connected_component(self.us.coords)  # Get nodes connected to us
        if len(connected_nodes) < threshold: # Threshold for being stuck in cage
            max_count = 0
            for node in connected_nodes:
                if len(self.map.graph.neighbours(node)) <= 3:  # If node has block neighbour
                    actual_neighbours = self.get_actual_neighbours(node)  # Get coords of neighbours regardless of graph
                    for neighbour in actual_neighbours:
                        if neighbour in self.map.block_library:
                            block_neighbours = self.get_actual_neighbours(neighbour)  # Get neighbours of block
                            for i in block_neighbours:
                                if i not in connected_nodes and i not in self.map.block_library:  # If node in new area
                                    count = len(nx.node_connected_component(i))  # Run the connected nodes
                                    if count > max_count:  # Calculate best node as one providing largest new area
                                        max_count = count
                                        best_node = node
        return best_node


    def get_actual_neighbours(self, node):
        x, y = node
        actual_neighbours = [((x+1), y), ((x-1), y), (x, (y+1)), (x, (y-1))]
        return actual_neighbours