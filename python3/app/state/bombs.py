from ..utilities import Entity


class Bomb:
    def __init__(self, entity):
        self.position = (entity["x"], entity["y"])
        self.radius = entity["blast_diameter"] // 2
        self.owner = str(entity["owner"])
        self.detonates_at = entity["expires"]
        self.detonated_by = []
        self.detonates = []
        self.impacts = None

    def update_tick(self, tick):
        if self.detonates_at - (self.radius + 2) <= tick:
            self.owner = None

    def calculate_impacts(self, map):
        impacts = []
        for i, m in [(1, 1), (0, 1), (1, -1), (0, -1)]:
            for r in range(1, self.radius + 1):
                new = list(self.position)
                new[i] += r * m
                new = tuple(new)
                impacts.append(tuple(new))
                if new not in map.graph or not map.graph.nodes[new].get("entity") in (
                    None,
                    Entity.BLAST,
                ):
                    break
        self.impacts = impacts

    def __hash__(self):
        return hash(self.position)

    def __eq__(self, other):
        return self.position == other.position


class BombLibrary:
    def __init__(self):
        self._bombs = {}
        self._coords = {}

    def add_bomb(self, entity, map):
        bomb = Bomb(entity)
        bomb.calculate_impacts(map)
        self._bombs[bomb.position] = bomb

    def remove_bomb(self, coords, map):
        bomb = self._bombs.get(coords)
        if bomb is not None:
            for b in bomb.detonates:
                b.detonated_by.remove(bomb)
            for b in bomb.detonated_by:
                b.detonates.remove(bomb)
            del self._bombs[bomb.position]

    def update(self, map):
        self._coords = {}
        for bomb in self._bombs.values():
            bomb.calculate_impacts(map)
            for coords in bomb.impacts:
                detonatee = self._bombs.get(coords)
                if detonatee is not None:
                    bomb.detonates.append(detonatee)
                    detonatee.detonated_by.append(bomb)
        for bomb in self._bombs.values():
            can_detonate = {
                bomb,
            }
            to_visit = bomb.detonated_by[:]
            while to_visit:
                current = to_visit.pop()
                can_detonate.add(current)
                to_visit.extend(
                    [b for b in current.detonated_by if b not in can_detonate]
                )
            for coords in bomb.impacts:
                if coords in self._coords:
                    self._coords[coords].update(can_detonate)
                else:
                    self._coords[coords] = set(can_detonate)

    def update_tick(self, tick):
        for bomb in self._bombs.values():
            bomb.update_tick(tick)

    def get_bomb_at(self, coords):
        return self._bombs.get(coords)

    def get_bombs_impacting(self, coords):
        return self._coords.get(coords, set())

    def get_bomb_impact_owners(self, coords):
        owners = set()
        for bomb in self.get_bombs_impacting(coords):
            owners.add(bomb.owner)
        return owners

    def get_bombs_owned_by(self, owner):
        bombs = []
        for bomb in self._bombs.values():
            print(bomb.owner, owner)
            if bomb.owner == owner:
                bombs.append(bomb)
        return bombs
