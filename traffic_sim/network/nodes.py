import random
from traffic_sim.vehicle import Vehicle

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
