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
        
        # NEW: Store configuration metadata for the report
        self.config_info = {}

    def set_config(self, sources, dt, total_steps, total_nodes, total_roads):
        """Stores simulation setup details for the final text report."""
        self.config_info = {
            "sources": sources,
            "dt": dt,
            "total_steps": total_steps,
            "total_nodes": total_nodes,
            "total_roads": total_roads
        }

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
        # 2. Throughput
        # ---------------------------------------------------------
        current_completed = 0
        for sink in sinks:
            completed_at_sink = sink.completed_count 
            
            current_completed += completed_at_sink
            self.sink_metrics[sink.node_id] = completed_at_sink
            
        self.history["throughput"].append(current_completed)

    def _generate_summary_text(self, sinks):
        """Generates a formatted string containing all summary statistics and configurations."""
        lines = []
        lines.append("\n" + "="*50)
        lines.append("SIMULATION STATISTIC SUMMARY")
        lines.append("="*50)
        
        if not self.history["time"]:
            lines.append("No data recorded.")
            return "\n".join(lines)

        # --- NEW: Append Configuration Details ---
        lines.append("\n[ Configuration Parameters ]")
        lines.append(f"  Time Step (dt):      {self.config_info.get('dt', 'N/A')} s")
        lines.append(f"  Total Steps:         {self.config_info.get('total_steps', 'N/A')}")
        lines.append(f"  Network Size:        {self.config_info.get('total_nodes', 0)} Nodes, {self.config_info.get('total_roads', 0)} Roads")
        
        lines.append("\n[ Traffic Generation Rates ]")
        sources = self.config_info.get("sources", {})
        if sources:
            for src_id, rate in sources.items():
                lines.append(f"  {src_id:<15}: {rate} vehicles/sec")
        else:
            lines.append("  No sources defined or recorded.")
        lines.append("-" * 50)

        # --- Existing Summary Output ---
        final_time = self.history["time"][-1]
        final_throughput = self.history["throughput"][-1]
        
        # Gather all exact wait times from all sinks
        all_wait_times = []
        for sink in sinks:
            all_wait_times.extend(sink.completed_wait_times)
            
        exact_avg_wait = sum(all_wait_times) / len(all_wait_times) if all_wait_times else 0
        throughput_rate = final_throughput / final_time if final_time > 0 else 0
        
        lines.append("\n[ Simulation Results ]")
        lines.append(f"Total Time Simulated:         {final_time:.1f} s")
        lines.append(f"Total Cars Completed:         {final_throughput}")
        lines.append(f"Exact Average Wait Time:      {exact_avg_wait:.2f} s per car")
        lines.append(f"Network Average Throughput:   {throughput_rate:.3f} cars/sec")
        
        lines.append("\nThroughput by Destination:")
        for sink_id, count in self.sink_metrics.items():
            rate = count / final_time if final_time > 0 else 0
            lines.append(f"  {sink_id:<15}: {count} cars ({rate:.3f} cars/sec)")
            
        lines.append("-" * 50)
        
        lines.append("Queue Lengths per Road:")
        for road_id, q_history in self.history["queue_lengths"].items():
            avg_q = sum(q_history) / len(q_history)
            max_q = max(q_history)
            lines.append(f"  {road_id:<15}: Avg {avg_q:.2f} cars | Max {max_q} cars")
            
        lines.append("="*50)
        
        return "\n".join(lines)

    def print_summary(self, sinks):
        """Prints the generated summary text to the terminal."""
        summary_text = self._generate_summary_text(sinks)
        print(summary_text)

    def save_summary_report(self, sinks, filename="simulation_summary.txt"):
        """Saves the generated summary text (terminal output + configs) to a file."""
        summary_text = self._generate_summary_text(sinks)
        
        save_dir = "results"
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        
        with open(filepath, "w") as f:
            f.write(summary_text)
            
        print(f"\nText summary successfully saved to: {filepath}")
    
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
        # Save the plot to the 'results' directory
        # ---------------------------------------------------------
        save_dir = "results"
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"\nPlots successfully saved to: {filepath}")

        # Display the plot on screen
        plt.show()
    
    def save_to_csv(self, filename="simulation_data.csv"):
        """Saves the recorded simulation history to a CSV file."""
        try:
            import pandas as pd
        except ImportError:
            print("\nCannot save CSV: pandas is not installed.")
            print("Run 'pip install pandas' in your terminal.")
            return

        # Prepare the primary time-series data
        df_base = pd.DataFrame({
            "Time": self.history["time"],
            "Throughput": self.history["throughput"],
            "Network_Backlog": self.history["network_backlog"]
        })

        # Flatten the queue_lengths dictionary into the main DataFrame
        for road_id, q_history in self.history["queue_lengths"].items():
            df_base[f"Queue_{road_id}"] = q_history

        import os
        save_dir = "results"
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        
        # Save to CSV
        df_base.to_csv(filepath, index=False)
        print(f"Simulation data successfully saved to: {filepath}")