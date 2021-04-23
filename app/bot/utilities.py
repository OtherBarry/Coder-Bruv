from enum import Enum


class Entity(str, Enum):
    """Enum for the different entity types"""

    AMMO = "a"
    BOMB = "b"
    POWERUP = "bp"
    METAL = "m"
    ORE = "o"
    FIRE = "t"  # Unclear?
    WOOD = "w"
    BLAST = "x"
