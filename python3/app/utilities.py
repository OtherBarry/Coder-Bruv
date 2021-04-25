from enum import Enum
import heapq


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
