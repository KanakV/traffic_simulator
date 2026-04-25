# network.py
# Defines the road network primitives used in the traffic simulation:
#   - Lane   : a single directional lane within a road segment
#   - Road   : a bidirectional road composed of multiple lanes
# Future extensions (Road, Junction, Sink, Source) can build on these classes.

from collections import deque


class Lane:
    """
    Represents a single directional lane within a road segment.

    Vehicles in a lane are stored in a deque ordered from rear to front
    (index 0 = rearmost vehicle, last index = frontmost vehicle).
    Movement is constrained so that no vehicle overtakes the one ahead of it,
    and all vehicles travel at the lane's speed limit (no individual speeds yet).

    Attributes:
        lane_id (str): Unique identifier for this lane.
        length (float): Physical length of the lane in metres.
        speed_limit (float): Maximum speed allowed in this lane (metres/second).
        vehicles (deque): Ordered collection of Vehicle objects currently in the lane,
                          arranged rear → front.
    """

    def __init__(self, lane_id, length, speed_limit):
        """
        Initialise a Lane.

        Args:
            lane_id (str): Unique identifier for the lane.
            length (float): Length of the lane in metres.
            speed_limit (float): Speed limit for the lane in metres/second.
        """
        self.lane_id = lane_id
        self.length = length
        self.speed_limit = speed_limit

        self.vehicles = deque()  # ordered: rear → front

    def is_empty(self):
        """
        Check whether the lane currently contains no vehicles.

        Returns:
            bool: True if the lane has no vehicles, False otherwise.
        """
        return len(self.vehicles) == 0

    def can_enter(self):
        """
        Check if a vehicle can enter the lane (space at start).

        A vehicle can enter only if the rearmost vehicle in the lane has
        already moved forward by at least its own length, leaving enough
        room at the start of the lane.

        Returns:
            bool: True if there is space for a new vehicle to enter, False otherwise.
        """
        if not self.vehicles:
            return True

        first_vehicle = self.vehicles[0]
        return first_vehicle.position > first_vehicle.length

    def add_vehicle(self, vehicle):
        """
        Place a vehicle at the start (position 0) of the lane.

        Fails silently (returns False) if there is not enough space at the
        lane entrance. On success the vehicle's position and current_lane
        attributes are updated.

        Args:
            vehicle: A Vehicle object to add to the lane.

        Returns:
            bool: True if the vehicle was successfully added, False if the lane
                  entrance is blocked.
        """
        if not self.can_enter():
            return False

        vehicle.position = 0.0
        vehicle.current_lane = self

        self.vehicles.appendleft(vehicle)  # insert at the rear of the deque
        return True

    def remove_vehicle(self, vehicle):
        """
        Remove a specific vehicle from the lane.

        Args:
            vehicle: The Vehicle object to remove.

        Returns:
            bool: True if the vehicle was found and removed, False otherwise.
        """
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)
            return True
        return False

    def step(self, dt):
        """
        Advance all vehicles in the lane by one simulation time-step.

        Vehicles move forward at the lane's speed limit, but are constrained
        so that no vehicle encroaches on the vehicle immediately ahead of it.
        The iteration goes front-to-rear so that each vehicle's new position
        is already known before the vehicle behind it is updated.

        Vehicles that reach or exceed `self.length` stay capped at `self.length`
        and are considered ready to exit (see `get_exit_ready`).

        Args:
            dt (float): Simulation time-step duration in seconds.
        """
        # Start with the lane end as the upper bound for the frontmost vehicle
        prev_position = self.length

        for vehicle in reversed(self.vehicles):  # front → rear order
            max_move = self.speed_limit * dt
            new_position = vehicle.position + max_move

            # Enforce no-overtaking / collision constraint with the vehicle ahead
            if new_position > prev_position - vehicle.length:
                new_position = prev_position - vehicle.length

            vehicle.position = min(new_position, self.length)
            prev_position = vehicle.position

    def get_exit_ready(self):
        """
        Return all vehicles that have reached or passed the end of the lane.

        These vehicles should be processed by the parent Road / Junction to
        either continue to the next road segment or be removed from the network.

        Returns:
            list: Vehicle objects whose position >= lane length.
        """
        return [v for v in self.vehicles if v.position >= self.length]

    def __repr__(self):
        return f"Lane({self.lane_id}, vehicles={len(self.vehicles)})"


class Road:
    """
    Represents a bidirectional road segment connecting two network nodes.

    A Road is composed of two sets of Lane objects:
      - forward_lanes : travel from node_a → node_b
      - backward_lanes: travel from node_b → node_a

    Each direction can have one or more parallel lanes (``lanes_per_dir``).
    When a vehicle is added, the first available lane in the requested direction
    is selected automatically.

    Attributes:
        road_id (str): Unique identifier for this road segment.
        node_a: The node at the "start" end of the road (forward direction origin).
        node_b: The node at the "end" of the road (forward direction destination).
        length (float): Physical length of the road in metres.
        capacity (int): Maximum number of vehicles the road is designed to carry
                        (informational; not currently enforced in code).
        speed_limit (float): Speed limit applied to all lanes on this road.
        forward_lanes (list[Lane]): Lanes for travel in the node_a → node_b direction.
        backward_lanes (list[Lane]): Lanes for travel in the node_b → node_a direction.
    """

    def __init__(self, road_id, node_a, node_b, length, capacity, speed_limit, lanes_per_dir=1):
        """
        Initialise a Road and create its constituent Lane objects.

        Args:
            road_id (str): Unique identifier for the road.
            node_a: Origin node (start of the forward direction).
            node_b: Destination node (end of the forward direction).
            length (float): Length of the road in metres.
            capacity (int): Intended vehicle capacity (informational).
            speed_limit (float): Speed limit in metres/second for all lanes.
            lanes_per_dir (int): Number of parallel lanes in each direction. Defaults to 1.
        """
        self.road_id = road_id
        self.node_a = node_a
        self.node_b = node_b

        self.length = length
        self.capacity = capacity
        self.speed_limit = speed_limit

        # Create lanes for each direction, named <road_id>_f_<index> / _b_<index>
        self.forward_lanes = [
            Lane(f"{road_id}_f_{i}", length, speed_limit)
            for i in range(lanes_per_dir)
        ]

        self.backward_lanes = [
            Lane(f"{road_id}_b_{i}", length, speed_limit)
            for i in range(lanes_per_dir)
        ]

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get_lanes(self, direction):
        """
        Return the list of lanes corresponding to the requested travel direction.

        Args:
            direction (str): Either "forward" (node_a → node_b) or
                             "backward" (node_b → node_a).

        Returns:
            list[Lane]: The lanes for that direction.

        Raises:
            ValueError: If ``direction`` is not "forward" or "backward".
        """
        if direction == "forward":
            return self.forward_lanes
        elif direction == "backward":
            return self.backward_lanes
        else:
            raise ValueError("Invalid direction")

    # -------------------------------------------------------------------------
    # Node accessors
    # -------------------------------------------------------------------------

    def get_start_node(self, direction):
        """
        Return the node from which vehicles begin travelling in the given direction.

        Args:
            direction (str): "forward" or "backward".

        Returns:
            The origin node for that direction (node_a for forward, node_b for backward).
        """
        return self.node_a if direction == "forward" else self.node_b

    def get_end_node(self, direction):
        """
        Return the node at which vehicles exit when travelling in the given direction.

        Args:
            direction (str): "forward" or "backward".

        Returns:
            The destination node for that direction (node_b for forward, node_a for backward).
        """
        return self.node_b if direction == "forward" else self.node_a

    # -------------------------------------------------------------------------
    # Vehicle management
    # -------------------------------------------------------------------------

    def add_vehicle(self, vehicle, direction):
        """
        Add a vehicle to the first available lane in the specified direction.

        Iterates through the lanes for the given direction and places the vehicle
        in the first lane whose entrance is unobstructed. The vehicle's
        ``current_road`` and ``direction`` attributes are updated on success.

        Args:
            vehicle: The Vehicle object to insert.
            direction (str): "forward" or "backward".

        Returns:
            bool: True if the vehicle was successfully added to a lane,
                  False if all lanes in that direction are blocked.
        """
        lanes = self._get_lanes(direction)

        # Simple strategy: pick first available lane
        for lane in lanes:
            if lane.add_vehicle(vehicle):
                vehicle.current_road = self
                vehicle.direction = direction
                return True

        return False

    def step(self, dt):
        """
        Advance all lanes (both directions) by one simulation time-step.

        Delegates to each Lane's ``step`` method.

        Args:
            dt (float): Simulation time-step duration in seconds.
        """
        for lane in self.forward_lanes + self.backward_lanes:
            lane.step(dt)

    def get_exit_vehicles(self, direction):
        """
        Collect all vehicles that are ready to exit the road in the given direction.

        A vehicle is ready to exit when its position has reached or exceeded the
        lane length. The caller (e.g. Junction) is responsible for actually
        removing them from their respective lanes and routing them onward.

        Args:
            direction (str): "forward" or "backward".

        Returns:
            list: All Vehicle objects at the end of any lane in that direction.
        """
        lanes = self._get_lanes(direction)
        vehicles = []

        for lane in lanes:
            vehicles.extend(lane.get_exit_ready())

        return vehicles

    def __repr__(self):
        return f"Road({self.road_id}, {self.node_a} <-> {self.node_b})"
