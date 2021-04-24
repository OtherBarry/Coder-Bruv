class Bomb:
    def __init__(self, entity):
        self.position = (entity["x"], entity["y"])
        self.radius = entity["bomb_diameter"] // 2
        self.owner = str(entity["owner"])
        self.detonated_by = []
        self.detonates = []

        self.potential_impact_coords = list(self._get_potential_impact())

    def _get_potential_impact(self):
        for r in range(1, self.radius + 1):
            for i, m in ((1, 1), (0, 1), (1, -1), (0, -1)):
                new = list(self.position)
                new[i] += r * m
                yield tuple(new)

    def get_impacts(self):
        pass
        # Get coords where explosion effects

class BombLibrary:
    def __init__(self):
        self.bombs = []
        self.coords = {}
        self.our_coords = []
        self.enemy_coords = []

    def add_bomb(self, entity):
        bomb = Bomb(entity)
        self.bombs.append(bomb)
        self.add_coords(bomb)


    def remove_bomb(self, coords):
        for bomb in self.bombs:
            if coords == bomb.position:
                self.bombs.remove(bomb)
            for coords in bomb.radius:
                for bombs in self.bombs:
                    if coords == bombs.position:
                        self.remove_bomb(coords)

    def update(self, map):
        # calculate actual impact
        # remake coords dict
        pass

    def add_coords(self, bomb):
        for coords in bomb.radius:
            if bomb.our_control:
                self.our_coords.append(coords)
            if bomb.enemy_control:
                self.enemy_coords.append(coords)

            for bombs in self.bombs:
                if coords == bombs.position:
                    bombs.assign_control(bomb.owner)
                    self.update_bomb_coords(bombs)

    def update_bomb_coords(self, bomb):
        for coords in bomb.radius:
            if bomb.our_control:
                self.our_coords.append(coords)
            if bomb.enemy_control:
                self.enemy_coords.append(coords)

    def who_has_control(self, coords):
        us = False
        them = False
        if coords in self.our_coords:
            us = True
        if coords in self.enemy_coords:
            them = True
        return us, them

    def is_there_bomb(self, coords):
        for bomb in self.bombs:
            if bomb.position == coords:
                return True
        return False
