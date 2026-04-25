# traffic_sim/direction.py

from enum import Enum

class Direction(Enum):
    FORWARD = 1   # node_a → node_b
    BACKWARD = 2  # node_b → node_a

    def opposite(self):
        return Direction.BACKWARD if self == Direction.FORWARD else Direction.FORWARD

