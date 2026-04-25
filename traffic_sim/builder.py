from traffic_sim.network.nodes import Source, Sink, Junction
from traffic_sim.network.links import Road
from traffic_sim.direction import Direction

def connect_bidirectional(n1, n2, road):
    """
    Properly links the road to the nodes in both directions, 
    setting up both entrances (incoming) and exits (outgoing).
    """
    # Forward direction: n1 to n2
    n1.add_outgoing(n2, road, Direction.FORWARD)
    n2.add_incoming(road, Direction.FORWARD)

    # Backward direction: n2 to n1
    n2.add_outgoing(n1, road, Direction.BACKWARD)
    n1.add_incoming(road, Direction.BACKWARD)

def connect_source(source, node, road):
    source.add_outgoing(node, road, Direction.FORWARD)
    node.add_incoming(road, Direction.FORWARD)

def connect_sink(node, sink, road):
    node.add_outgoing(sink, road, Direction.FORWARD)
    sink.add_incoming(road, Direction.FORWARD)  


class NetworkBuilder:
    def __init__(self):
        self.nodes = []
        self.roads = []

    def add_node(self, node, pos=None, destinations=None):
        """Adds a node, optionally setting its position and destinations."""
        if pos:
            node.pos = pos
        if destinations:
            node.destinations = destinations
        self.nodes.append(node)
        return node

    def add_road(self, road_id, node_a, node_b, speed_limit, capacity, bidirectional=False):
        """Creates a road and automatically detects the right way to connect it."""
        road = Road(road_id, node_a, node_b, speed_limit, capacity)
        self.roads.append(road)

        # Auto-detect connection type based on the class of the nodes
        if isinstance(node_a, Source):
            connect_source(node_a, node_b, road)
        elif isinstance(node_b, Sink):
            connect_sink(node_a, node_b, road)
        elif bidirectional:
            connect_bidirectional(node_a, node_b, road)
        else:
            # Standard one-way junction-to-junction fallback
            node_a.add_outgoing(node_b, road, Direction.FORWARD)
            node_b.add_incoming(road, Direction.FORWARD)
            
        return road

    def build(self):
        """Initializes the router and applies it to all relevant nodes."""
        from traffic_sim.engine import DynamicRouter as Router
        router = Router(self.nodes)
        
        # Give the router to any node that has a 'router' attribute
        for node in self.nodes:
            if hasattr(node, 'router') or isinstance(node, (Source, Junction)):
                node.router = router
                
        return self.nodes, self.roads