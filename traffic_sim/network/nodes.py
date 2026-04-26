import random
from traffic_sim.vehicle import Vehicle
import math

class Node:
    def __init__(self, node_id):
        self.node_id = node_id
        self.pos = None

        # Graph connectivity
        self.incoming = []   # [(road, direction)]
        self.outgoing = []   # [(road, direction)]
        self.neighbors = {}  # node → [(road, direction)]

    def add_incoming(self, road, direction):
        self.incoming.append((road, direction))

    def add_outgoing(self, node, road, direction):
        if node not in self.neighbors:
            self.neighbors[node] = []
        self.neighbors[node].append((road, direction))
        self.outgoing.append((road, direction))

    def get_neighbors(self):
        return list(self.neighbors.keys())

    def get_connections(self, target_node):
        return self.neighbors.get(target_node, [])

    def step(self, dt):
        """Default: do nothing"""
        pass

    def __repr__(self):
        return f"Node({self.node_id})"

class RoundaboutJunction(Node):
    def __init__(self, node_id, capacity=8, full_loop_time=3.0):
        super().__init__(node_id)
        self.router = None
        self.capacity = capacity
        self.full_loop_time = full_loop_time
        self.vehicles_in_circle = []

    def step(self, dt):
        # PHASE 1: Move and Exit
        for entry in self.vehicles_in_circle[:]:
            entry['timer'] -= dt
            if entry['timer'] <= 0:
                v = entry['veh']
                next_road = entry['exit_road']
                path = self.router.get_shortest_path(self, v.destination)
                if path:
                    _, next_dir = path[0]
                    if next_road.add_vehicle(v, next_dir):
                        self.vehicles_in_circle.remove(entry)
                else:
                    self.vehicles_in_circle.remove(entry)

        # PHASE 2: Entrance
        if len(self.vehicles_in_circle) < self.capacity:
            waiting = []
            for road, direction in self.incoming:
                ready = road.get_exit_ready(direction)
                if ready: waiting.append((ready[0], road, direction))
            
            if waiting:
                v, in_road, in_dir = random.choice(waiting)
                path = self.router.get_shortest_path(self, v.destination)
                if path:
                    out_road, _ = path[0]
                    
                    # Calculate angles for smooth animation
                    # math.atan2(y, x) gives the angle of the road relative to the junction
                    in_pos = in_road.node_a.pos if in_road.node_b == self else in_road.node_b.pos
                    out_pos = out_road.node_b.pos if out_road.node_a == self else out_road.node_a.pos
                    
                    start_angle = math.atan2(in_pos[1] - self.pos[1], in_pos[0] - self.pos[0])
                    end_angle = math.atan2(out_pos[1] - self.pos[1], out_pos[0] - self.pos[0])
                    
                    # Ensure we travel clockwise
                    if end_angle < start_angle:
                        end_angle += 2 * math.pi
                    
                    # Travel time proportional to the angular distance
                    angular_dist = end_angle - start_angle
                    travel_time = (angular_dist / (2 * math.pi)) * self.full_loop_time
                    # Minimum travel time so it doesn't "teleport" to an adjacent exit
                    travel_time = max(travel_time, 0.5)

                    in_road.remove_vehicle(v, in_dir)
                    self.vehicles_in_circle.append({
                        'veh': v, 
                        'exit_road': out_road, 
                        'timer': travel_time,
                        'total_time': travel_time,
                        'start_angle': start_angle,
                        'end_angle': end_angle
                    })

class TrafficSignalJunction(Node):
    def __init__(self, node_id, green_time=5.0, processing_delay=0.3): 
        super().__init__(node_id)
        self.router = None
        
        self.processing_delay = processing_delay
        self.timer = 0.0
        self.current_vehicle = None 
        
        self.green_time = green_time
        self.phase_timer = green_time
        self.active_index = 0

    def step(self, dt):
        if not self.incoming:
            return

        # Helper function to check if an incoming road has a queue
        def has_queue(index):
            road, direction = self.incoming[index]
            return len(road.get_exit_ready(direction)) > 0

        # ---------------------------------------------------------
        # PHASE 0: Smart Traffic Light Update (Demand-Responsive)
        # ---------------------------------------------------------
        self.phase_timer -= dt
        
        # We switch the light IF the timer runs out OR the current green light is empty
        if self.phase_timer <= 0 or not has_queue(self.active_index):
            next_index = -1
            
            # Loop through the other roads to find who needs the green light next.
            # We check up to len(self.incoming) so that if only the CURRENT road
            # has a queue, it will just re-trigger its own green light!
            for i in range(1, len(self.incoming) + 1):
                check_idx = (self.active_index + i) % len(self.incoming)
                if has_queue(check_idx):
                    next_index = check_idx
                    break
            
            if next_index != -1:
                # Give the green light to the first road we found with a queue
                self.active_index = next_index
                self.phase_timer = self.green_time
            else:
                # No roads have any cars waiting. Idle the timer at 0 until someone arrives.
                self.phase_timer = 0.0

        # ---------------------------------------------------------
        # PHASE 1: A vehicle is physically inside the intersection
        # ---------------------------------------------------------
        if self.current_vehicle is not None:
            if self.timer > 0:
                self.timer -= dt
                return
            
            v = self.current_vehicle
            if not v.destination:
                self.current_vehicle = None 
                return
                
            path = self.router.get_shortest_path(self, v.destination)
            if not path:
                self.current_vehicle = None
                return
                
            next_road, next_dir = path[0]
            
            if next_road.add_vehicle(v, next_dir):
                self.current_vehicle = None 
            return

        # ---------------------------------------------------------
        # PHASE 2: Intersection empty. Intake from the GREEN road.
        # ---------------------------------------------------------
        # Only pull a car if the currently active road actually has a queue
        if has_queue(self.active_index):
            active_road, active_dir = self.incoming[self.active_index]
            ready_to_exit = active_road.get_exit_ready(active_dir)
            
            v = ready_to_exit[0]
            active_road.remove_vehicle(v, active_dir)
            self.current_vehicle = v
            self.timer = self.processing_delay

# Junction with delay and scheduling 
class Junction(Node):
    def __init__(self, node_id, processing_delay=0.3): # Default 1 sec delay
        super().__init__(node_id)
        self.router = None
        self.processing_delay = processing_delay
        self.timer = 0.0
        
        # NEW: The intersection physically holds exactly one vehicle
        self.current_vehicle = None 

    def step(self, dt):
        # ---------------------------------------------------------
        # PHASE 1: A vehicle is currently inside the intersection
        # ---------------------------------------------------------
        if self.current_vehicle is not None:
            # Count down the timer while the car crosses
            if self.timer > 0:
                self.timer -= dt
                return
            
            # Timer is done! Try to push the car onto the next road
            v = self.current_vehicle
            if not v.destination:
                self.current_vehicle = None # Drop invalid vehicle
                return
                
            path = self.router.get_shortest_path(self, v.destination)
            if not path:
                self.current_vehicle = None
                return
                
            next_road, next_dir = path[0]
            
            if next_road.add_vehicle(v, next_dir):
                # Success! The vehicle has left the intersection
                self.current_vehicle = None 
            
            # If add_vehicle fails (the next road is full), we do nothing.
            # The car stays trapped in self.current_vehicle, blocking the junction!
            return

        # ---------------------------------------------------------
        # PHASE 2: The intersection is empty. Look for the next car.
        # ---------------------------------------------------------
        waiting_vehicles = []
        for incoming_road, incoming_dir in self.incoming:
            ready_to_exit = incoming_road.get_exit_ready(incoming_dir)
            if ready_to_exit:
                waiting_vehicles.append((ready_to_exit[0], incoming_road, incoming_dir))

        if not waiting_vehicles:
            return

        # Pick a random road's front car to enter the intersection
        v, incoming_road, incoming_dir = random.choice(waiting_vehicles)

        # Pull it OFF the road and INTO the intersection
        incoming_road.remove_vehicle(v, incoming_dir)
        self.current_vehicle = v
        self.timer = self.processing_delay

# Minimal Working Junction
class MinimalJunction(Node):
    def __init__(self, node_id):
        super().__init__(node_id)

    def step(self, dt):
        for incoming_road, incoming_dir in self.incoming:
            ready_to_exit = incoming_road.get_exit_ready(incoming_dir)

            for v in ready_to_exit:
                if not v.path:
                    # Vehicle reached the end of its path but isn't at a sink!
                    # For safety, remove it from the simulation so it doesn't block traffic
                    incoming_road.remove_vehicle(v, incoming_dir)
                    continue
                
                # Look at the vehicle's next required road
                next_road, next_dir = v.path[0]

                # Try to move vehicle onto the next road
                if next_road.add_vehicle(v, next_dir):
                    # Success: remove from the old road AND pop the path queue
                    incoming_road.remove_vehicle(v, incoming_dir)
                    v.path.pop(0)
                else:
                    # Blocked: stay at the end of the current road (Wait in traffic)
                    v.position = incoming_road.length

# Random Junction
class RandomJunction(Node):
    def __init__(self, node_id):
        super().__init__(node_id)

    def step(self, dt):
        """
        Pulls vehicles from incoming roads and pushes them to outgoing roads.
        """
        for incoming_road, incoming_dir in self.incoming:
            # Using the new simplified Road method
            ready_to_exit = incoming_road.get_exit_ready(incoming_dir)

            for v in ready_to_exit:
                if not self.outgoing:
                    continue
                
                # Currently: Random routing logic
                # Pick a random outgoing connection
                next_road, next_dir = random.choice(self.outgoing)

                # Try to move vehicle onto the next road
                if next_road.add_vehicle(v, next_dir):
                    # Success: remove from the old road
                    incoming_road.remove_vehicle(v, incoming_dir)
                else:
                    # Blocked: stay at the end of the current road
                    v.position = incoming_road.length

class Source(Node):
    # Pass in the router and a list of possible destination nodes
    def __init__(self, node_id, generation_rate, router=None):
        super().__init__(node_id)
        self.generation_rate = generation_rate
        self.counter = 0
        
        self.router = router
        self.destinations = None

    def add_incoming(self, road, direction):
        raise ValueError(f"Source node '{self.node_id}' cannot have incoming connections.")

    def generate_vehicle(self):
        vid = f"{self.node_id}_v{self.counter}"
        self.counter += 1
        
        # Pick a random sink as the destination
        destination = random.choice(self.destinations)
        v = Vehicle(vid, source=self, destination=destination)
        
        # Calculate the route and give it to the vehicle
        v.path = self.router.get_shortest_path(self, destination)
        return v

    def step(self, dt):
        if random.random() < self.generation_rate * dt:
            v = self.generate_vehicle()
            
            if not v.path:
                print(f"Warning: No path found for {v.vehicle_id}. Dropping vehicle.")
                return

            # Read the FIRST step of the path
            first_road, first_dir = v.path[0]
            
            # Try to enter the road. If successful, remove that step from the path
            if first_road.add_vehicle(v, first_dir):
                v.path.pop(0)

class Sink(Node):
    def __init__(self, node_id):
        super().__init__(node_id)
        # CHANGE: Replaced the list with a simple integer counter
        self.completed_count = 0
        self.completed_wait_times = []
        self.color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))

    def accept_vehicle(self, vehicle):
        # CHANGE: Just increment the counter
        self.completed_count += 1
        self.completed_wait_times.append(vehicle.total_wait_time)
        
        # Because we don't save the 'vehicle' object anywhere, 
        # Python will automatically delete it from RAM right after this!

    def step(self, dt):
        """
        Pulls vehicles off incoming roads and removes them from the simulation.
        """
        for incoming_road, incoming_dir in self.incoming:
            ready_to_exit = incoming_road.get_exit_ready(incoming_dir)
            
            for v in ready_to_exit:
                self.accept_vehicle(v)
                incoming_road.remove_vehicle(v, incoming_dir)
