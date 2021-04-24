import networkx as nx

from ..utilities import Entity


class Map:
    """Graph representation of the game map"""

    IMPASSABLE_ENTITIES = [Entity.BOMB, Entity.METAL, Entity.ORE, Entity.WOOD]
    WEIGHT_MAP = {
        Entity.AMMO: -1,
        Entity.POWERUP: -10,
        Entity.BLAST: 1000,
        "Future Blast Zone": 100,
    }

    def __init__(self, world, entities):
        self._width = world["width"]
        self._height = world["height"]
        self.graph = nx.grid_2d_graph(self._width, self._height)
        self._bombs = dict()
        for node in self.graph.nodes:
            self.graph.nodes[node]["weight"] = 0
        for entity in entities:
            self.add_entity(entity)

    def _generate_edges(self, coords):
        x, y = coords
        for to in (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1):
            if to in self.graph:
                yield coords, to

    def _get_bomb_impacted_coords(self, bomb_coords):
        x, y = bomb_coords
        for i in range(1, self._bombs[bomb_coords] + 1):
            for coords in (x + i, y), (x - i, y), (x, y + i), (x, y - i):
                if coords in self.graph:
                    yield coords

    def add_entity(self, entity):
        """Adds the given entity to the map"""
        coords = (entity["x"], entity["y"])
        entity_type = entity["type"]
        if entity_type in Map.IMPASSABLE_ENTITIES:
            if entity_type == Entity.BOMB:
                self._bombs[coords] = entity["blast_diameter"] // 2
                for impacted_coords in self._get_bomb_impacted_coords(coords):
                    self.graph.nodes[impacted_coords]["weight"] += Map.WEIGHT_MAP[
                        "Future Blast Zone"
                    ]
            self.graph.remove_node(coords)
        else:
            self.graph.nodes[coords]["entity"] = entity_type
            self.graph.nodes[coords]["weight"] += Map.WEIGHT_MAP[entity_type]

    def remove_entity(self, coords):
        """Removes an entity from the map at the given coordinates"""
        # TODO: Handle multiple bomb blast zones
        # TODO: Handle removal of bomb barrier prior to detonation
        if coords in self.graph:
            self.graph.nodes[coords]["weight"] -= Map.WEIGHT_MAP[
                self.graph.nodes[coords]["entity"]
            ]
            del self.graph.nodes[coords]["entity"]
        else:
            if coords in self._bombs:
                for impacted_coords in self._get_bomb_impacted_coords(coords):
                    self.graph.nodes[impacted_coords]["weight"] -= Map.WEIGHT_MAP[
                        "Future Blast Zone"
                    ]
                del self._bombs[coords]
            self.graph.add_node(coords, weight=0)
            self.graph.add_edges_from(self._generate_edges(coords))
