# traffic_sim/visualiser.py

import matplotlib.pyplot as plt
import math

class Visualiser:
    def __init__(self):
        self.fig, self.ax = plt.subplots()

    def render(self, nodes, roads, t=0):
        self.ax.clear()

        # -----------------------------
        # Draw roads
        # -----------------------------
        for road in roads:
            x1, y1 = road.node_a.pos
            x2, y2 = road.node_b.pos
            self.ax.text((x1+x2)/2, (y1+y2)/2, str(road.road_id))


            self.ax.plot([x1, x2], [y1, y2], 'k-', linewidth=2)

        # -----------------------------
        # Draw nodes
        # -----------------------------
        for node in nodes:
            x, y = node.pos

            if hasattr(node, "received"):      # Sink
                color = "red"
            elif hasattr(node, "generation_rate"):  # Source
                color = "green"
            else:
                color = "blue"

            self.ax.scatter(x, y, c=color, s=100)
            self.ax.text(x, y, str(node.node_id))

            if hasattr(node, "current_vehicle") and node.current_vehicle is not None:
                self.ax.scatter(node.pos[0], node.pos[1], c="red", s=50, zorder=15)

        # -----------------------------
        # Draw vehicles (UPDATED)
        # -----------------------------
        for road in roads:
            for v in road.forward_vehicles:
                x, y = self._vehicle_position(road, v)
                self.ax.scatter(x, y, c="orange", s=20)
                
            for v in road.backward_vehicles:
                x, y = self._vehicle_position(road, v)
                self.ax.scatter(x, y, c="orange", s=20)

        # -----------------------------
        self.ax.set_title(f"Time: {t:.2f}")
        self.ax.set_aspect('equal')
        plt.pause(0.01)

    # -----------------------------
    def _vehicle_position(self, road, vehicle):
        """
        Convert vehicle position → (x, y)
        Handles direction properly
        """
        if vehicle.direction.name == "FORWARD":
            start = road.node_a
            end = road.node_b
        else:
            start = road.node_b
            end = road.node_a

        x1, y1 = start.pos
        x2, y2 = end.pos

        ratio = vehicle.position / road.length

        x = x1 + ratio * (x2 - x1)
        y = y1 + ratio * (y2 - y1)

        return x, y
        
    # Use later: For multi lanes
    # def _vehicle_position(self, road, vehicle):
    #     from traffic_sim.direction import Direction

    #     if vehicle.direction == Direction.FORWARD:
    #         start = road.node_a
    #         end = road.node_b
    #         lane_index = road.forward_lanes.index(vehicle.current_lane)
    #     else:
    #         start = road.node_b
    #         end = road.node_a
    #         lane_index = road.backward_lanes.index(vehicle.current_lane)

    #     x1, y1 = start.pos
    #     x2, y2 = end.pos

    #     ratio = vehicle.position / road.length

    #     # Base position
    #     x = x1 + ratio * (x2 - x1)
    #     y = y1 + ratio * (y2 - y1)

    #     # Perpendicular offset
    #     dx = x2 - x1
    #     dy = y2 - y1
    #     length = math.hypot(dx, dy)

    #     if length > 0:
    #         nx = -dy / length
    #         ny = dx / length

    #         offset = (lane_index - 0.5) * 2  # tweak spacing
    #         x += nx * offset
    #         y += ny * offset

    #     return x, y

