import os

class StatisticTracker:
    def __init__(self):
        self.history = {
            "time": [],
            "throughput": [],        
            "network_backlog": [],   
            "queue_lengths": {}      
        }
        self.last_t = 0.0
        self.total_wait_time = 0.0   
        self.sink_metrics = {}       

    def _count_queue(self, road, direction):
        """
        Counts how many vehicles are stacked up bumper-to-bumper 
        behind the stop line.
        """
        vehicles = road._get_vehicles(direction)
        queue_count = 0
        
        # The expected position of the first waiting car
        expected_position = road.length - road.stop_margin
        
        # Iterate from the front of the line to the rear
        for v in reversed(vehicles):
            # If the car is right up against the stop line or the car in front of it
            # (We use a 0.1 margin to account for floating-point math)
            if v.position >= expected_position - 0.1:
                queue_count += 1
                # The next car in the queue should be right behind this one
                expected_position = v.position - v.length
            else:
                # We found a gap! The traffic jam ends here.
                break
                
        return queue_count

    def record_step(self, t, roads, sinks):
        dt = t - self.last_t
        self.last_t = t
        
        self.history["time"].append(t)
        
        # ---------------------------------------------------------
        # 1. Queue Lengths & Wait Times
        # ---------------------------------------------------------
        total_waiting_network_wide = 0
        
        from traffic_sim.direction import Direction
        for road in roads:
            # NEW: Count the actual contiguous traffic jams
            fwd_q = self._count_queue(road, Direction.FORWARD)
            bwd_q = self._count_queue(road, Direction.BACKWARD)
            total_q = fwd_q + bwd_q
            
            if road.road_id not in self.history["queue_lengths"]:
                self.history["queue_lengths"][road.road_id] = []
                
            self.history["queue_lengths"][road.road_id].append(total_q)
            total_waiting_network_wide += total_q
            
        self.history["network_backlog"].append(total_waiting_network_wide)
        
        # Accumulate total wait time based on ALL queued vehicles
        self.total_wait_time += total_waiting_network_wide * dt

        # ---------------------------------------------------------
        # 3. Throughput
        # ---------------------------------------------------------
        current_completed = 0
        for sink in sinks:
            # FIX: Use the new integer counter instead of len(sink.received)
            completed_at_sink = sink.completed_count 
            
            current_completed += completed_at_sink
            self.sink_metrics[sink.node_id] = completed_at_sink
            
        self.history["throughput"].append(current_completed)

    def print_summary(self, sinks):
        print("\n" + "="*50)
        print("SIMULATION STATISTIC SUMMARY")
        print("="*50)
        
        if not self.history["time"]:
            print("No data recorded.")
            return

        final_time = self.history["time"][-1]
        final_throughput = self.history["throughput"][-1]
        
        # Gather all exact wait times from all sinks
        all_wait_times = []
        for sink in sinks:
            all_wait_times.extend(sink.completed_wait_times)
            
        exact_avg_wait = sum(all_wait_times) / len(all_wait_times) if all_wait_times else 0
        throughput_rate = final_throughput / final_time if final_time > 0 else 0
        
        print(f"Total Time Simulated:         {final_time:.1f} s")
        print(f"Total Cars Completed:         {final_throughput}")
        print(f"Exact Average Wait Time:      {exact_avg_wait:.2f} s per car")
        print(f"Network Average Throughput:   {throughput_rate:.3f} cars/sec")
        
        print("\nThroughput by Destination:")
        for sink_id, count in self.sink_metrics.items():
            rate = count / final_time if final_time > 0 else 0
            print(f"  {sink_id:<15}: {count} cars ({rate:.3f} cars/sec)")
            
        print("-" * 50)
        
        print("Queue Lengths per Road:")
        for road_id, q_history in self.history["queue_lengths"].items():
            avg_q = sum(q_history) / len(q_history)
            max_q = max(q_history)
            print(f"  {road_id:<15}: Avg {avg_q:.2f} cars | Max {max_q} cars")
            
        print("="*50)
    
    def plot_results(self, filename="simulation_dashboard.png"):
        """Generates line graphs of the simulation statistics and saves them to a folder."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("\nCannot generate plots: matplotlib is not installed.")
            print("Run 'pip install matplotlib' in your terminal to view graphs.")
            return

        if not self.history["time"]:
            print("No data to plot.")
            return

        time = self.history["time"]

        # Create a figure with 3 stacked subplots
        fig, axs = plt.subplots(3, 1, figsize=(10, 12))

        # ---------------------------------------------------------
        # Plot 1: Network Backlog (Queueing Delay Indicator)
        # ---------------------------------------------------------
        axs[0].plot(time, self.history["network_backlog"], color='firebrick', linewidth=2)
        axs[0].set_title("Network Backlog vs. Time")
        axs[0].set_xlabel("Time (seconds)")
        axs[0].set_ylabel("Total Vehicles Waiting")
        axs[0].grid(True, linestyle='--', alpha=0.7)

        # ---------------------------------------------------------
        # Plot 2: Cumulative Throughput
        # ---------------------------------------------------------
        axs[1].plot(time, self.history["throughput"], color='seagreen', linewidth=2)
        axs[1].set_title("Cumulative Throughput vs. Time")
        axs[1].set_xlabel("Time (seconds)")
        axs[1].set_ylabel("Total Vehicles Completed")
        axs[1].grid(True, linestyle='--', alpha=0.7)

        # ---------------------------------------------------------
        # Plot 3: Queue Lengths per Road
        # ---------------------------------------------------------
        plotted_roads = False
        for road_id, q_history in self.history["queue_lengths"].items():
            if max(q_history) > 0:
                axs[2].plot(time, q_history, label=f"Road {road_id}")
                plotted_roads = True
                
        axs[2].set_title("Queue Lengths per Road vs. Time")
        axs[2].set_xlabel("Time (seconds)")
        axs[2].set_ylabel("Queue Length (vehicles)")
        axs[2].grid(True, linestyle='--', alpha=0.7)
        
        if plotted_roads:
            axs[2].legend(bbox_to_anchor=(1.02, 1), loc='upper left')
        else:
            axs[2].text(0.5, 0.5, 'No queues formed during simulation', 
                        horizontalalignment='center', verticalalignment='center', 
                        transform=axs[2].transAxes)

        plt.tight_layout()

        # ---------------------------------------------------------
        # NEW: Save the plot to the 'results' directory
        # ---------------------------------------------------------
        # 1. Ensure the 'results' directory exists
        save_dir = "results"
        os.makedirs(save_dir, exist_ok=True)
        
        # 2. Construct the full file path
        filepath = os.path.join(save_dir, filename)
        
        # 3. Save the figure (dpi=300 ensures it is high quality/crisp)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"\nPlots successfully saved to: {filepath}")

        # 4. Display the plot on screen (Optional: remove this if you ONLY want it saved)
        plt.show()
