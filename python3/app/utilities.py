import math
from enum import Enum
import heapq


class Entity(str, Enum):
    """Enum for the different entity types"""

    AMMO = "a"
    BOMB = "b"
    POWERUP = "bp"
    METAL = "m"
    ORE = "o"
    WOOD = "w"
    BLAST = "x"


class PriorityQueue:
    """Implementation of a priority queue using a heap."""

    def __init__(self, values=None):
        if values is None:
            self.size = 0
            self.heap = []
        else:
            self.size = len(values)
            self.heap = values
        heapq.heapify(self.heap)

    def is_empty(self):
        """Returns whether the queue is empty in O(1)"""
        return self.size == 0

    def push(self, item):
        """Adds an item to the queue in O(log n)"""
        heapq.heappush(self.heap, item)
        self.size += 1

    def pop(self):
        """Retrieves the min item from the queue in O(log n)"""
        val = heapq.heappop(self.heap)
        self.size -= 1
        return val


WEIGHT_MAP = {
    Entity.AMMO: 90,
    Entity.POWERUP: 5,
    "Fire": 20000,
    Entity.BLAST: 10000,
    "Them Future Blast": 5000,
    "Trap": 2500,
    "Us Future Blast": 1000,
    "Enemy - in_bad_spot": 200,
    "Invincibility Cutoff": 2501,
    "Default": 100,
    "Enemy": -1,
    "Enemy - next_to": math.inf,
    "Danger": 1001,
}


FIRE_SPAWN_MAP = {
    1800: (0, 8),
    1805: (8, 0),
    1810: (1, 8),
    1815: (7, 0),
    1820: (2, 8),
    1825: (6, 0),
    1830: (3, 8),
    1835: (5, 0),
    1840: (4, 8),
    1845: (4, 0),
    1850: (5, 8),
    1855: (3, 0),
    1860: (6, 8),
    1865: (2, 0),
    1870: (7, 8),
    1875: (1, 0),
    1880: (8, 8),
    1885: (0, 0),
    1890: (8, 7),
    1895: (0, 1),
    1900: (8, 6),
    1905: (0, 2),
    1910: (8, 5),
    1915: (0, 3),
    1920: (8, 4),
    1925: (0, 4),
    1930: (8, 3),
    1935: (0, 5),
    1940: (8, 2),
    1945: (0, 6),
    1950: (8, 1),
    1955: (0, 7),
    1960: (7, 1),
    1965: (1, 7),
    1970: (6, 1),
    1975: (2, 7),
    1980: (5, 1),
    1985: (3, 7),
    1990: (4, 1),
    1995: (4, 7),
    2000: (3, 1),
    2005: (5, 7),
    2010: (2, 1),
    2015: (6, 7),
    2020: (1, 1),
    2025: (7, 7),
    2030: (1, 2),
    2035: (7, 6),
    2040: (1, 3),
    2045: (7, 5),
    2050: (1, 4),
    2055: (7, 4),
    2060: (1, 5),
    2065: (7, 3),
    2070: (1, 6),
    2075: (7, 2),
    2080: (2, 6),
    2085: (6, 2),
    2090: (3, 6),
    2095: (5, 2),
    2100: (4, 6),
    2105: (4, 2),
    2110: (5, 6),
    2115: (3, 2),
    2120: (6, 6),
    2125: (2, 2),
    2130: (6, 5),
    2135: (2, 3),
    2140: (6, 4),
    2145: (2, 4),
    2150: (6, 3),
    2155: (2, 5),
    2160: (5, 3),
    2165: (3, 5),
    2170: (4, 3),
    2175: (4, 5),
    2180: (3, 3),
    2185: (5, 5),
    2190: (3, 4),
    2195: (5, 4),
    2200: (4, 4),
}
