# Traffic Simulation Network (EE5150)

A custom, discrete-time microscopic traffic simulation engine written in Python. This project simulates individual vehicles navigating through a road network, complete with dynamic routing, congestion metrics, junction delays, and intersection management.

## Features

- **Microscopic Kinematics**: Vehicles are simulated individually. They move along roads respecting speed limits, physical vehicle lengths, safety margins, and traffic jams (bumper-to-bumper queueing).
- **Dynamic Routing**: Uses a custom `DynamicRouter` (Dijkstra's Algorithm) that calculates the shortest path while actively factoring in real-time traffic congestion on links using a custom BPR (Bureau of Public Roads) function. A classic static `DijkstraRouter` is also available.
- **Node Variants**:
  - `Source`: Generates traffic at a specified rate (Poisson/Random).
  - `Sink`: Consumes vehicles and records their exact wait times upon reaching their destination.
  - `Junction`: Represents intersections. Supports crossing delays where intersections securely handle one car at a time. Contains alternative variants (`MinimalJunction` and `RandomJunction`).
- **Network Builder**: Provides an easy-to-use graph API for defining bidirectional or single-direction multi-lane roads, specifying capacities, and automatically interpreting forward/backward traversals.
- **Detailed Statistics Tracking**: Calculates granular statistics such as Average Wait Time per car, Total Throughput, and average queue backlog per individual road over the course of the simulation.
- **Live Visualization**: A 2D visualizer that renders nodes, road identifiers, and physical vehicle movement.

## Project Structure

```text
assignment_6/
├── main.py                  # Simulation entry point and network definition
└── traffic_sim/             # Core library
    ├── builder.py           # NetworkBuilder API for constructing the simulation graph
    ├── direction.py         # Enums for bi-directional road mapping (FORWARD/BACKWARD)
    ├── engine.py            # Routing algorithms (DynamicRouter, DijkstraRouter)
    ├── stats.py             # StatisticTracker for logging waits, queues, and throughput
    ├── vehicle.py           # Vehicle state (position, route, wait time)
    ├── visualiser.py        # Graph rendering (Matplotlib/Pygame based)
    └── network/             
        ├── links.py         # Road segment logic (kinematics, queue processing)
        └── nodes.py         # Intersection & endpoint logic (Source, Sink, Junctions)
```

## Setup & Running

This project requires a Python 3 environment.

1. Install dependencies (e.g. `matplotlib` or `pygame` as required by the visualiser):
   ```bash
   pip install matplotlib
   ```
2. Execute the main program:
   ```bash
   python main.py
   ```

### Simulation Configuration
You can configure major simulation variables at the top of `main.py`:
- `TOTAL_STEPS`: Number of simulation frames to compute.
- `DT`: The time delta (in seconds) simulated per step.

## Architecture

- **Step Cycle**: The simulation progresses via a rigid `step(dt)` tick. 
  1. *Roads* update first: vehicles physically advance based on max speed limits but are strictly clamped by the stop line or the vehicle in front of them, calculating pure delay based on distance constrained.
  2. *Nodes* update second: `Junction` objects observe ready vehicles at the endpoints of incoming roads, apply arbitrary delays, and pop vehicles off roads onto the next designated road in their previously computed journey. 
  3. *Statistics & Render*: Real-time data is sent to the `StatisticTracker` to update the global network backlog.

## Contributors
- Kanak Varma - ED23B027
- Medha Girish - EE23B112
