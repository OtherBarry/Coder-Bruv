import networkx as nx

from .bombs import BombLibrary
from ..utilities import Entity


class Map:
    """Graph representation of the game map"""

    IMPASSABLE_ENTITIES = [Entity.BOMB, Entity.METAL, Entity.ORE, Entity.WOOD]
    WEIGHT_MAP = {
        Entity.AMMO: -10,
        Entity.POWERUP: -100,
        Entity.BLAST: 10000,
        "Future Blast Zone": 1000,
        "Default": 100,
    }

    def __init__(self, world, entities):
        self._width = world["width"]
        self._height = world["height"]
        self.graph = nx.grid_2d_graph(self._width, self._height)
        self.bomb_library = BombLibrary()
        for node in self.graph.nodes:
            self.graph.nodes[node]["weight"] = Map.WEIGHT_MAP["Default"]
        for entity in entities:
            self.add_entity(entity)

    def _generate_edges(self, coords):
        x, y = coords
        for to in (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1):
            if to in self.graph:
                yield coords, to


    def add_entity(self, entity):
        """Adds the given entity to the map"""
        coords = (entity["x"], entity["y"])
        entity_type = entity["type"]
        if entity_type in Map.IMPASSABLE_ENTITIES:
            if entity_type == Entity.BOMB:
                self.bomb_library.add_bomb(entity, self)
            self.graph.remove_node(coords)
        else:
            self.graph.nodes[coords]["entity"] = entity_type
            self.graph.nodes[coords]["weight"] += Map.WEIGHT_MAP[entity_type]

    def remove_entity(self, coords):
        """Removes an entity from the map at the given coordinates"""
        if coords in self.graph:
            self.graph.nodes[coords]["weight"] -= Map.WEIGHT_MAP[
                self.graph.nodes[coords]["entity"]
            ]
            del self.graph.nodes[coords]["entity"]
        else:
            if self.bomb_library.get_bomb_at(coords) is not None:
                self.bomb_library.remove_bomb(coords, self)
            self.graph.add_node(coords, weight=Map.WEIGHT_MAP["Default"])
            self.graph.add_edges_from(self._generate_edges(coords))
