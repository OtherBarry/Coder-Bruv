import asyncio
import math
import os

import networkx as nx

from ..server_connection import ServerConnection
from ..state.bombs import Bomb
from ..utilities import Entity, PriorityQueue

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
        cached_weight = self.node_weights.get(node)
        if cached_weight is not None:
            return cached_weight
        if node not in self.map.graph:
            return 0
        weight = self.map.graph.nodes[node]["weight"]
        bomb_owners = self.map.bomb_library.get_bomb_impact_owners(node)
        if self.them.id in bomb_owners or None in bomb_owners:
            weight += self.map.WEIGHT_MAP[Entity.BLAST]
        elif self.us.id in bomb_owners:
            weight += 1
        if self.us.is_invulnerable:
            weight = min(self.map.WEIGHT_MAP[Entity.BLAST] // 2, weight)
        entrance = self.danger_nodes.get(node)
        if node == self.them.coords:
            if self.next_to_enemy:
                weight += math.inf
            else:
                us_weight = self._get_node_weight(self.us.coords)
                if us_weight > self.map.WEIGHT_MAP["Default"]:
                    weight += 125
                elif self.state.tick < 1800 and self.us.hp > 1:
                    weight -= 1
        if entrance is not None:
            valid = True
            try:
                us_to_entrance = nx.shortest_path_length(
                    self.map.graph, self.us.coords, entrance
                )
                them_to_entrance = nx.shortest_path_length(
                    self.map.graph, self.them.coords, entrance
                )
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                valid = False
            if valid and (them_to_entrance <= 2 or us_to_entrance >= them_to_entrance):
                weight += self.map.WEIGHT_MAP[Entity.BLAST] // 2
        self.node_weights[node] = weight
        return weight

    def _get_edge_weight(self, start, end, properties):
        return self._get_node_weight(start) + self._get_node_weight(end)

    def _get_path_to_best(self, value_func):
        best_nodes = PriorityQueue()
        for node, data in self.map.graph.nodes(data=True):
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
            if node in self.paths[self.us.coords]:
                worst_node = max(
                    (
                        self._get_node_weight(n)
                        for n in self.paths[self.us.coords][node][1:]
                    ),
                    default=self._get_node_weight(self.us.coords),
                )
                best_nodes.push(
                    (
                        self._get_node_weight(node),
                        worst_node,
                        _manhattan_to_centre(node),
                        self.distances[self.us.coords][node],
                        node,
                    )
                )

        if not best_nodes.is_empty():
            _, worst_node, _, _, target = best_nodes.pop()
            if worst_node <= self._get_node_weight(self.us.coords):
                return self.paths[self.us.coords][target]
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
        current_enemy_distance = -_manhattan_distance(self.us.coords, self.them.coords)
        best = PriorityQueue()
        for neighbour in neighbours:
            non_blast_node = False
            connected_nodes = nx.node_connected_component(self.map.graph, neighbour)
            for node in connected_nodes:
                if not self.map.bomb_library.get_bombs_impacting(node):
                    non_blast_node = True
            if not non_blast_node:
                continue
            neigbour_weight = self._get_node_weight(neighbour)
            best.push(
                (
                    neigbour_weight >= self.map.WEIGHT_MAP[Entity.BLAST],
                    _manhattan_distance(neighbour, self.them.coords)
                    > current_enemy_distance,
                    -len(connected_nodes),
                    neigbour_weight,
                    neighbour,
                )
            )
        if neighbours:
            return best.pop()[-1]
        return None

    async def _on_game_tick(self, tick_number, game_state):
        if game_state is not self.state:
            self.state = game_state
            self.map = game_state.map
            self.us = game_state.us
            self.them = game_state.them

        self.node_weights = {}

        self.danger_nodes = self._find_danger_nodes()
        self.next_to_enemy = _manhattan_distance(self.us.coords, self.them.coords) == 1

        detonatable_bombs = [
            b
            for b in self.map.bomb_library.get_bombs_impacting(self.them.coords)
            if b.owner == self.us.id
        ]

        # Dismount or chadonate bomb if just planted
        if self.us.coords not in self.map.graph:
            if self.us.hp >= 2 > self.them.hp and not self.them.is_invulnerable:
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
                (
                    self.us.hp >= 2 > self.them.hp
                    or bomb
                    not in self.map.bomb_library.get_bombs_impacting(self.us.coords)
                )
                and not self.them.is_invulnerable
                and self.them.coords in bomb.impacts
            ):
                await self._server.send_detonate(*bomb.position)
                print("DETONATING ", end=" | ")
                return

        # Plant bomb if abundance of ammo and space and next to enemy
        if (
            self.us.coords not in self.danger_nodes
            and self.next_to_enemy
            and (self.us.ammo > self.them.hp or self.us.ammo == self.them.hp == 1)
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
        if self.us.ammo:
            escape = self.prison_break()
            bomb = self.map.bomb_library.get_bomb_at(escape)
            if bomb is not None:
                print("ESCAPING   ", end=" | ")
                await self._server.send_detonate(*bomb.position)
                return
            if escape is not None:
                if (
                    escape == self.us.coords
                    and self._get_node_weight(escape)
                    <= self.map.WEIGHT_MAP[Entity.BLAST]
                ):
                    print("DEMOLISHING", end=" | ")
                    await self._server.send_bomb()
                    return
                else:
                    path = self.paths[self.us.coords][escape]
                    worst_node = max(self._get_node_weight(n) for n in path)
                    if worst_node <= self.map.WEIGHT_MAP["Default"]:
                        move = _get_direction_from_coords(self.us.coords, path[1])
                        print("PLANNING   ", end=" | ")
                        await self._server.send_move(move)
                        return

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
        optimal_path = self._get_path_to_best(self._get_node_weight)

        if optimal_path is not None and len(optimal_path) > 1:
            print("IMPROVING  ", end=" | ")
            move = _get_direction_from_coords(self.us.coords, optimal_path[1])
            await self._server.send_move(move)
            return
        print("WAITING    ", end=" | ")

    def prison_break(self):
        if (
            self.them.coords not in self.map.graph
            or self.them.coords in self.paths[self.us.coords]
        ):
            return None
        bombs = self.map.bomb_library.get_bombs_owned_by(self.us.id)
        if bombs:
            bad_bombs = self.map.bomb_library.get_bombs_impacting(self.us.coords)
            for bomb in bombs:
                if bomb not in bad_bombs:
                    return bomb.position
            return None
        connected_nodes = nx.node_connected_component(
            self.map.graph, self.us.coords
        )  # Get nodes connected to us
        if len(connected_nodes) > len(
            nx.node_connected_component(self.map.graph, self.them.coords)
        ):
            return None
        best_nodes = PriorityQueue()
        for node in connected_nodes:
            if len(self.map.graph[node]) < 4:  # If node has block neighbour
                destruction_value = 0
                actual_neighbours = self.get_actual_neighbours(
                    node
                )  # Get coords of neighbours regardless of graph
                for neighbour in actual_neighbours:
                    hp = self.map.block_library.get(neighbour)
                    if hp is not None:
                        destruction_value += 1 if hp > 1 else 2
                        block_neighbours = self.get_actual_neighbours(
                            neighbour
                        )  # Get neighbours of block
                        for i in block_neighbours:
                            if (
                                i not in connected_nodes and i in self.map.graph
                            ):  # If node in new area
                                destruction_value += (
                                    len(nx.node_connected_component(self.map.graph, i))
                                    / hp
                                )  # Run the connected nodes
                if destruction_value > 0:
                    best_nodes.push((-destruction_value, node))
        while not best_nodes.is_empty():
            x, y = best_nodes.pop()[1]
            bomb = Bomb(
                {
                    "x": x,
                    "y": y,
                    "blast_diameter": self.us.blast_diameter,
                    "owner": self.us.id,
                    "expires": self.state.tick + 40,
                }
            )
            bomb.calculate_impacts(self.map)
            for node in connected_nodes:
                if node != (x, y) and node not in bomb.impacts:
                    return x, y
        return None

    def get_actual_neighbours(self, node):
        x, y = node
        actual_neighbours = [((x + 1), y), ((x - 1), y), (x, (y + 1)), (x, (y - 1))]
        return actual_neighbours
