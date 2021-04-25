from queue import Queue


class Bomb:
    def __init__(self, entity):
        self.position = (entity["x"], entity["y"])
        self.radius = entity["blast_diameter"] // 2
        self.owner = str(entity["owner"])
        self.detonated_by = []
        self.detonates = []
        self.impacts = None

    def calculate_impacts(self, map):
        self.impacts = []
        for i, m in [(1, 1), (0, 1), (1, -1), (0, -1)]:
            for r in range(1, self.radius + 1):
                new = list(self.position)
                new[i] += r * m
                new = tuple(new)
                if new not in map.graph:
                    break
                self.impacts.append(tuple(new))
                if map.graph.nodes[new].get("entity") is not None:
                    break

    def __hash__(self):
        return hash(self.position)

    def __eq__(self, other):
        return self.position == other.position


class BombLibrary:
    def __init__(self):
        self._bombs = {}
        self._coords = {}
        self._expanded_coords_cache = {}

    def add_bomb(self, entity):
        bomb = Bomb(entity)
        self._bombs[bomb.position] = bomb

    def remove_bomb(self, coords, map):
        bomb = self._bombs.get(coords)
        if bomb is not None:
            for coord in bomb.impacts:
                bombs = self._coords.get(coord)
                if bombs is not None:
                    if len(bombs) == 1:
                        del self._coords[coord]
                        map.graph.nodes[coord]["weight"] = map.WEIGHT_MAP["Default"]
                    else:
                        bombs.remove(bomb)
            for b in bomb.detonates:
                try:
                    b.detonated_by.remove(bomb)
                except ValueError:
                    pass
            for b in bomb.detonated_by:
                try:
                    b.detonates.remove(bomb)
                except ValueError:
                    pass
            del self._bombs[bomb.position]

    def update(self, map):
        self._coords = {}
        for bomb in self._bombs.values():  # O(b)
            bomb.calculate_impacts(map)
            for coord in bomb.impacts:  # O(b.i)
                if coord in self._coords:
                    self._coords[coord].append(bomb)
                else:
                    self._coords[coord] = [bomb]
        for bomb in self._bombs.values():  # O(b)
            bombs = self._coords.get(bomb.position)
            if bombs is not None:
                bomb.detonated_by.extend([b for b in bombs if b is not bomb])  # O(b.db)
            for coord in bomb.impacts:  # O(b.i)
                bombs = self._coords.get(coord)
                if bombs is not None:
                    bomb.detonates.extend([b for b in bombs if b is not bomb])  # O(b.d)
        for coords in self._coords:
                map.graph.nodes[coords]["weight"] = map.WEIGHT_MAP[
                    "Future Blast Zone"
                ]

        print("Bombs: {} | Bomb Coords: {}".format(len(self._bombs), len(self._coords)), end=" | ")

    def get_bomb_at(self, coords):
        return self._bombs.get(coords)

    def get_bombs_impacting(self, coords):
        value = self._expanded_coords_cache.get(coords)
        if value is not None:
            return value
        bombs = set()
        to_visit = Queue()
        for bomb in self._coords.get(coords, []):
            to_visit.put(bomb)
        while not to_visit.empty():
            current = to_visit.get()
            if current in bombs:
                continue
            bombs.add(current)
            for bomb in current.detonated_by:
                to_visit.put(bomb)
        value = list(bombs)
        self._expanded_coords_cache[coords] = value
        return value

    def get_bomb_impact_owners(self, coords):
        owners = set()
        for bomb in self.get_bombs_impacting(coords):
            owners.add(bomb.owner)
        return list(owners)
