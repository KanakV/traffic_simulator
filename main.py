import time
import random

from traffic_sim.network.nodes import Source, Sink
# from traffic_sim.network.nodes import Junction
from traffic_sim.network.nodes import TrafficSignalJunction as Junction
# from traffic_sim.network.nodes import RoundaboutJunction as Junction
from traffic_sim.network.links import Road
from traffic_sim.direction import Direction
from traffic_sim.vehicle import Vehicle
from traffic_sim.visualiser import Visualiser
from traffic_sim.engine import DynamicRouter as Router
from traffic_sim.builder import NetworkBuilder
from traffic_sim.stats import StatisticTracker

# -----------------------------
# Config
# -----------------------------
TOTAL_STEPS = 500
DT = 0.1

# -----------------------------
# Main Simulation
# -----------------------------
def main():
    print("Initializing Simulation...")
    builder = NetworkBuilder()

    src1 = builder.add_node(Source("SRC1", generation_rate=1), pos=(0, 0))
    src2 = builder.add_node(Source("SRC2", generation_rate=1), pos=(60, 20))
    sink1 = builder.add_node(Sink("SNK1"), pos=(75, 0))
    sink2 = builder.add_node(Sink("SNK2"), pos=(10, 20))
    j1 = builder.add_node(Junction("J1"), pos=(25, 0))
    j2 = builder.add_node(Junction("J2"), pos=(50, 0))

    builder.add_road("R1", src1, j1, 15, 20)
    builder.add_road("R3", j1, j2, 15, 20, bidirectional=True)
    builder.add_road("R2", j2, sink1, 15, 20)
    builder.add_road("R4", src2, j2, 15, 20)
    builder.add_road("R5", j1, sink2, 15, 20)

    src1.destinations = [sink1]
    src2.destinations = [sink2]


    # # 1. Create Nodes (and set their positions immediately)
    # src1  = builder.add_node(Source("SRC1", generation_rate=2), pos=(0, 0))
    # src2  = builder.add_node(Source("SRC2", generation_rate=4), pos=(100, -100))
    # src3  = builder.add_node(Source("SRC3", generation_rate=6), pos=(-100, 100))
    # sink1 = builder.add_node(Sink("SNK1"), pos=(-100, -50))
    # sink2 = builder.add_node(Sink("SNK2"), pos=(150, 100))
    # sink3 = builder.add_node(Sink("SNK3"), pos=(150, -100))

    # j1    = builder.add_node(Junction("J1"), pos=(70, 0))
    # j2    = builder.add_node(Junction("J2"), pos=(150, 50))
    # j3    = builder.add_node(Junction("J3"), pos=(-100, -150))
    # j4    = builder.add_node(Junction("J4"), pos=(100, 100))

    # # Assign destinations
    # src1.destinations = [sink1, sink2, sink3]
    # src2.destinations = [sink1, sink2, sink3]
    # src3.destinations = [sink1, sink2, sink3]

    # # 2. Create Roads (Builder auto-connects them!)
    # builder.add_road("R1", src1, j1, 15, 20)
    # builder.add_road("R2", j1, j2, 20, 20, bidirectional=True)
    # builder.add_road("R3", j1, sink2, 15, 20)
    # builder.add_road("R4", src2, j2, 25, 30)
    # builder.add_road("R5", src2, j1, 15, 20)
    # builder.add_road("R6", j1, j3, 20, 20, bidirectional=True)
    # builder.add_road("R7", src2, j3, 15, 20)
    # builder.add_road("R8", j3, sink1, 15, 20)
    # builder.add_road("R9", j2, sink2, 15, 20)
    # builder.add_road("R10", src3, j4, 15, 20)
    # builder.add_road("R11", j4, sink3, 15, 20)
    # builder.add_road("R12", j4, sink1, 15, 20)
    # builder.add_road("R13", j2, j4, 15, 20, bidirectional=True)

    # 3. Finalize and extract nodes/roads
    nodes, roads = builder.build()
    sinks = [n for n in nodes if isinstance(n, Sink)]
    
    # NEW: Extract source generation rates to pass to the tracker
    sources = {n.node_id: n.generation_rate for n in nodes if isinstance(n, Source)}
    
    tracker = StatisticTracker()
    
    # NEW: Pass the configuration to the tracker so it can be logged
    tracker.set_config(
        sources=sources, 
        dt=DT, 
        total_steps=TOTAL_STEPS,
        total_nodes=len(nodes),
        total_roads=len(roads)
    )

    # 4. Initialize Visualiser
    try:
        # Toggle record_gif=True to save a GIF, or False to save memory
        vis = Visualiser(record_gif=False) 
        has_visualiser = True
    except NameError:
        print("Visualiser not found. Running in headless mode.")
        has_visualiser = False

    # 5. Simulation parameters
    dt = DT
    total_steps = TOTAL_STEPS

    # Main Loop
    print("Starting Simulation Loop...")
    for step in range(total_steps):
        t = step * dt

        # Step A: Update vehicle kinematics (Roads)
        for road in roads:
            road.step(dt)

        # Step B: Process routing, spawning, and consuming (Nodes)
        for node in nodes:
            node.step(dt)

        # Step C: Record Statistics
        tracker.record_step(t, roads, sinks)
        
        # Step D: Render visual frame
        if has_visualiser:
            vis.render(nodes, roads, t)
            time.sleep(0.1)
        elif step % 10 == 0:
            for r in roads: print(f"  {r}")
            print("-" * 40)
            
        # Initial pause so you can see the setup before it starts moving
        # if step == 1:
        #     input("Press Enter to continue...")

    # -----------------------------
    # Simulation Complete Output
    # -----------------------------
    tracker.print_summary(sinks)
    
    # NEW: Save the summary report to a text file
    tracker.save_summary_report(sinks, "simulation_summary.txt")
    
    if has_visualiser:
        vis.save_gif()
        
    tracker.plot_results()
    tracker.save_to_csv("simulation_data.csv")

if __name__ == "__main__":
    main()