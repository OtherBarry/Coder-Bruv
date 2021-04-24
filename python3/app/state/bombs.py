class Bomb:
    def __init__(self, coords, owner, radius):
        self.position = coords
        self.radius = radius
        self.owner = owner
        self.our_control = False
        self.enemy_control = False
        self.assign_control(owner)

        BombLibrary.add_bomb(self)

    def assign_control(self, owner):
        if owner == 0:
            self.our_control = True
        else:
            self.enemy_control = True

    def get_impacts:
        # Get coords where explosion effects

class BombLibrary:
    def __init__(self):
        self.bombs = []
        self.our_coords = []
        self.enemy_coords = []

    def add_bomb(self, bomb):
        self.bombs.append(bomb)
        self.add_coords(bomb)

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
        answer = False
        for bomb in self.bombs:
            if coords == bomb.position:
                answer = True
                break
        return answer

    def remove_bomb(self, coords):
        for bomb in self.bombs:
            if coords == bomb.position:
                self.bombs.remove(bomb)
            for coords in bomb.radius:
                for bombs in self.bombs:
                    if coords == bombs.position:
                        self.remove_bomb(coords)
