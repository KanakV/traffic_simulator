# traffic_sim/vehicle.py

class Vehicle:
    def __init__(self, vehicle_id, source, destination=None, length=5.0):
        self.vehicle_id = vehicle_id
        self.source = source
        self.destination = destination

        self.position = 0.0
        self.current_road = None
        self.direction = None

        self.path = []

        self.length = length
        self.total_wait_time = 0.0 

    # -----------------------------
    def __repr__(self):
        return f"Vehicle({self.vehicle_id})"