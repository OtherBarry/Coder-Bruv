from enum import Enum


class Entity(str, Enum):
    """Enum for the different entity types"""

    AMMO = "a"
    BOMB = "b"
    BLAST = "x"
    POWERUP = "bp"
    METAL = "m"
    ORE = "o"
    WOOD = "w"
