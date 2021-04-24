import asyncio
import os
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

def spiral_from_coords(coords):
    moves = [(1, 1), (0, 1), (1, -1), (0, -1)]
    yield coords
    coords = list(coords)
    visited = [coords]
    i = 0
    while True:
        d, m = moves[i]
        new_coords = coords[:]
        new_coords[d] += m
        coords = new_coords
        if not (0 <= coords[0] <= 9 and 0 <= coords[1] <= 9):
            break
        if coords in visited:
            i = (i - 1) % len(moves)
            continue
        yield tuple(coords)
        visited.append(coords)
        i = (i + 1) % len(moves)



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

    def _get_path_to_best(self):
        best = None
        for node, data in self.map.graph.nodes(data=True):
            if node in self.map.graph and data["weight"] < self.map.graph.nodes[self.us.coords]["weight"]:
                try:
                    path = nx.shortest_path(self.map.graph, self.us.coords, node, self._get_weight)
                except nx.NetworkXNoPath:
                    continue
                if path:
                    mean_weight = sum(self.map.graph.nodes[x]["weight"] for x in path) / len(path)
                    if best is None:
                        best = (mean_weight, path)
                    elif mean_weight < best[0]:
                        best = (mean_weight, path)

        if best is not None:
            return best[1]

    def _get_path_to_centre(self):
        # TODO: Stop from infinite loop problems
        for target in spiral_from_coords((4, 4)):
            if target in self.map.graph:
                try:
                    path = nx.shortest_path(self.map.graph, self.us.coords, target, self._get_weight)
                except nx.NetworkXNoPath:
                    continue
                if path and (sum(self.map.graph.nodes[x]["weight"] for x in path) / len(path)) < max(101, self.map.graph.nodes[self.us.coords]["weight"]):
                    return path

    async def _on_game_tick(self, tick_number, game_state):
        if game_state is not self.state:
            self.state = game_state
            self.map = game_state.map
            self.us = game_state.us
            self.them = game_state.them

        path = self._get_path_to_best()
        # if :
        #     path = self._get_path_to_centre()
        if path is not None and len(path) > 1:
            move = _get_direction_from_coords(self.us.coords, path[1])
            await self._server.send_move(move)
            return
        # print("No Move Returned")
