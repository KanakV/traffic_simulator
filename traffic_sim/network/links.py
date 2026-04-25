import math
from collections import deque
from traffic_sim.direction import Direction

class Road:
    def __init__(self, road_id, node_a, node_b, speed_limit, capacity=10):
        self.road_id = road_id
        self.node_a = node_a
        self.node_b = node_b

        # Calculates the physical length based on node coordinates
        self.length = math.dist(node_a.pos, node_b.pos)
        self.stop_margin = 5
        self.speed_limit = speed_limit
        self.capacity = capacity

        # Direct queues for bidirectional traffic (rear → front)
        self.forward_vehicles = deque()
        self.backward_vehicles = deque()

    # -----------------------------
    def _get_vehicles(self, direction: Direction):
        """Helper to fetch the correct queue based on direction."""
        if direction == Direction.FORWARD:
            return self.forward_vehicles
        elif direction == Direction.BACKWARD:
            return self.backward_vehicles
        else:
            raise ValueError("Invalid direction")

    def get_start_node(self, direction: Direction):
        return self.node_a if direction == Direction.FORWARD else self.node_b

    def get_end_node(self, direction: Direction):
        return self.node_b if direction == Direction.FORWARD else self.node_a

    # -----------------------------
    def can_enter(self, direction: Direction):
        """Check capacity and physical spacing at entry for a given direction."""
        vehicles = self._get_vehicles(direction)
        
        if len(vehicles) >= self.capacity:
            return False

        if not vehicles:
            return True

        first_vehicle = vehicles[0]
        return first_vehicle.position > first_vehicle.length

    def add_vehicle(self, vehicle, direction: Direction):
        """Attempts to add a vehicle to the road in the specified direction."""
        if not self.can_enter(direction):
            return False

        vehicle.position = 0.0
        vehicle.current_road = self
        vehicle.direction = direction

        self._get_vehicles(direction).appendleft(vehicle)
        return True

    def remove_vehicle(self, vehicle, direction: Direction):
        """Removes a vehicle from the road (usually when transitioning to a node)."""
        vehicles = self._get_vehicles(direction)
        if vehicle in vehicles:
            vehicles.remove(vehicle)
            return True
        return False

    # -----------------------------
    def step(self, dt):
        """Updates vehicle positions for both directions."""
        self._step_direction(self.forward_vehicles, dt)
        self._step_direction(self.backward_vehicles, dt)

    def _step_direction(self, vehicles, dt):
        """The core kinematic logic, applied to a specific directional queue."""
        stop_line = self.length - self.stop_margin
        
        # Set the initial 'car ahead' to infinity so the front car can reach the end
        prev_position = float('inf') 

        for vehicle in reversed(vehicles):
            max_move = self.speed_limit * dt
            desired_position = vehicle.position + max_move

            # Calculate actual allowed position (clamped by stop line or car ahead)
            allowed_position = min(desired_position, stop_line)
            allowed_position = min(allowed_position, prev_position - vehicle.length)
            
            # NEW: Calculate exact delay
            # How far did we physically move compared to how far we wanted to move?
            actual_move = max(0, allowed_position - vehicle.position)
            
            if actual_move < max_move:
                # If we moved half our max distance, half of this dt was spent "waiting"
                delay_fraction = 1.0 - (actual_move / max_move)
                vehicle.total_wait_time += (delay_fraction * dt)
            
            # Update the vehicle position to the clamped value
            vehicle.position = allowed_position
            
            # This vehicle becomes the 'car ahead' for the next one in line
            prev_position = vehicle.position

    def get_exit_ready(self, direction: Direction):
        """Returns a list of vehicles that have reached the end of the road."""
        vehicles = self._get_vehicles(direction)
        stop_line = self.length - self.stop_margin
        return [v for v in vehicles if v.position >= stop_line]

    def __repr__(self):
        return (f"Road({self.road_id}, "
                f"Fwd:{len(self.forward_vehicles)}/{self.capacity}, "
                f"Bwd:{len(self.backward_vehicles)}/{self.capacity})")

