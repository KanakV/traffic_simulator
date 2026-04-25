# traffic_sim/router.py
import heapq

class DynamicRouter:
    def __init__(self, nodes, alpha=2.0, beta=2.0):
        self.nodes = nodes
        # Tuning parameters for how much congestion affects routing
        self.alpha = alpha  
        self.beta = beta    

    def get_shortest_path(self, start_node, end_node):
        """
        Calculates the dynamically fastest path using Dijkstra's algorithm,
        factoring in real-time traffic congestion on links.
        """
        # We are tracking "time" now, not just "distance"
        costs = {n: float('infinity') for n in self.nodes}
        costs[start_node] = 0
        
        previous = {n: None for n in self.nodes}
        pq = [(0, id(start_node), start_node)]

        while pq:
            current_cost, _, current_node = heapq.heappop(pq)

            if current_node == end_node:
                break

            if current_cost > costs[current_node]:
                continue

            for neighbor, connections in current_node.neighbors.items():
                road, direction = connections[0]
                
                # ---------------------------------------------------
                # DYNAMIC EDGE WEIGHT CALCULATION
                # ---------------------------------------------------
                # 1. Base travel time (Free-flow conditions)
                free_flow_time = road.length / road.speed_limit
                
                # 2. Current congestion metrics
                # We use max(1, capacity) to prevent divide-by-zero errors
                num_vehicles = len(road._get_vehicles(direction))
                capacity = max(1, road.capacity)
                
                # 3. Apply the BPR function for congestion penalty
                utilization = num_vehicles / capacity
                penalty = 1 + self.alpha * (utilization ** self.beta)
                
                # Final edge weight is the estimated time to cross
                travel_time = free_flow_time * penalty
                # ---------------------------------------------------

                total_cost = current_cost + travel_time

                if total_cost < costs[neighbor]:
                    costs[neighbor] = total_cost
                    previous[neighbor] = (current_node, road, direction)
                    heapq.heappush(pq, (total_cost, id(neighbor), neighbor))

        path = []
        curr = end_node
        while curr != start_node:
            prev_data = previous[curr]
            if prev_data is None:
                return [] 
            
            prev_node, road, direction = prev_data
            path.append((road, direction))
            curr = prev_node

        return path[::-1]


class DijkstraRouter:
    def __init__(self, nodes):
        self.nodes = nodes

    def get_shortest_path(self, start_node, end_node):
        """
        Calculates the shortest path using Dijkstra's algorithm.
        Returns a list of tuples: [(road, direction), (road, direction), ...]
        """
        distances = {n: float('infinity') for n in self.nodes}
        distances[start_node] = 0
        
        # Stores how we reached a node: {node: (prev_node, road, direction)}
        previous = {n: None for n in self.nodes}
        
        # Priority queue: (distance, id(node), node)
        # We use id(node) as a tie-breaker so Python doesn't try to compare Node objects
        pq = [(0, id(start_node), start_node)]

        while pq:
            current_dist, _, current_node = heapq.heappop(pq)

            # If we reached the destination, we can stop searching
            if current_node == end_node:
                break

            # Optimization: skip if we found a shorter path already
            if current_dist > distances[current_node]:
                continue

            for neighbor, connections in current_node.neighbors.items():
                # Grab the first available road connecting these two nodes
                road, direction = connections[0]
                
                # The weight is the length of the road
                weight = road.length 
                distance = current_dist + weight

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = (current_node, road, direction)
                    heapq.heappush(pq, (distance, id(neighbor), neighbor))

        # Reconstruct the path backwards from the destination
        path = []
        curr = end_node
        while curr != start_node:
            prev_data = previous[curr]
            if prev_data is None:
                return [] # No path exists!
            
            prev_node, road, direction = prev_data
            path.append((road, direction))
            curr = prev_node

        # Reverse the path so it goes from start -> end
        return path[::-1]