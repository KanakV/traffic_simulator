import pygame
import math
from traffic_sim.direction import Direction
try:
    from PIL import Image
except ImportError:
    Image = None

class Visualiser:
    def __init__(self, record_gif=False):
        pygame.init()
        
        # 1. Setup Window (occupying most of the screen)
        info = pygame.display.Info()
        # Fallback for headless testing
        if info.current_w <= 0 or info.current_h <= 0:
            self.width, self.height = 1280, 720
        else:
            self.width = int(info.current_w * 0.8)
            self.height = int(info.current_h * 0.8)
            
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Traffic Simulator - PiP Inspection Mode")
        
        # -----------------------------
        # Minimalist Flat Palette
        # -----------------------------
        self.color_bg = (30, 34, 40)          # Deep Charcoal
        self.color_road = (80, 85, 95)        # Muted Slate
        self.color_source = (46, 204, 113)    # Emerald Green
        self.color_sink = (231, 76, 60)       # Alizarin Red (Also used for max load)
        self.color_junc = (52, 152, 219)      # Peter River Blue
        self.color_veh = (236, 240, 241)      # Cloud White
        self.color_veh_pip = (241, 196, 15)   # Sunflower Yellow (For zoomed vehicles)
        self.color_text = (189, 195, 199)     # Silver
        self.color_ui_bg = (44, 62, 80)       # Darker Blue for box background
        
        # Typography
        self.font = pygame.font.SysFont("segoeui, arial, sans-serif", 14, bold=True)
        self.font_lg = pygame.font.SysFont("segoeui, arial, sans-serif", 18, bold=True)
        
        # Camera & Coordinate System
        self.camera_initialized = False
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # -----------------------------
        # PiP Zoom Configuration
        # -----------------------------
        self.selected_node = None # Stores the node object currently in focus
        self.zoom_box_size = 250   # Size of the square PiP box
        self.zoom_magnification = 6.0 # How much to zoom relative to standard map

        self.record_gif = record_gif
        self.frames = []

    def _init_camera(self, nodes):
        """Calculates default scaling and offset to fit the network on screen."""
        if not nodes: return
        min_x = min(n.pos[0] for n in nodes if n.pos)
        max_x = max(n.pos[0] for n in nodes if n.pos)
        min_y = min(n.pos[1] for n in nodes if n.pos)
        max_y = max(n.pos[1] for n in nodes if n.pos)
        span_x, span_y = max(max_x - min_x, 1), max(max_y - min_y, 1)

        # Scale network to take up 70% of available window space
        scale_x = (self.width * 0.7) / span_x
        scale_y = (self.height * 0.7) / span_y
        self.scale = min(scale_x, scale_y)

        # Find the center and calculate offset
        self.offset_x = (self.width / 2) - (((min_x + max_x) / 2) * self.scale)
        self.offset_y = (self.height / 2) - (((min_y + max_y) / 2) * self.scale)
        self.camera_initialized = True

    def _map_coords(self, pos, scale=None, ox=None, oy=None):
        """Standardizes coordinate transformation, allowing for local overrides (for PiP)."""
        s = scale or self.scale
        tx = ox if ox is not None else self.offset_x
        ty = oy if oy is not None else self.offset_y
        return (int(pos[0] * s + tx), int(pos[1] * s + ty))

    def render(self, nodes, roads, t):
        if not self.camera_initialized: self._init_camera(nodes)

        # Handle Events (Input)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                # Check if a node was clicked (simple radius check)
                self.selected_node = None # Deselect by default
                for node in nodes:
                    px, py = self._map_coords(node.pos)
                    if math.hypot(mx - px, my - py) < 20:
                        self.selected_node = node
                        break

        self.screen.fill(self.color_bg)

        # =========================================================
        # 1. DRAW STANDARD MAP (Static view)
        # =========================================================
        # Draw Roads & Load Indicators
        for road in roads:
            start_pos = self._map_coords(road.node_a.pos)
            end_pos = self._map_coords(road.node_b.pos)
            
            # --- NEW: Calculate Load & Determine Color ---
            fwd_load = len(road._get_vehicles(Direction.FORWARD))
            bwd_load = len(road._get_vehicles(Direction.BACKWARD))
            current_load = fwd_load + bwd_load
            max_load = getattr(road, 'capacity', 10) # Change 10 to a sensible default if capacity is missing
            
            # Switch to red if maximum capacity is reached
            road_color = self.color_sink if current_load >= max_load else self.color_road
            
            pygame.draw.line(self.screen, road_color, start_pos, end_pos, 4)
            
            # --- NEW: Render Load Text at Road Midpoint ---
            mid_x = (start_pos[0] + end_pos[0]) / 2
            mid_y = (start_pos[1] + end_pos[1]) / 2
            
            # Use red text if overloaded to make it stand out more
            text_color = self.color_sink if current_load >= max_load else self.color_text
            load_text = self.font.render(f"{current_load}/{max_load}", True, text_color)
            
            # Center the text slightly above the road line
            text_rect = load_text.get_rect(center=(int(mid_x), int(mid_y - 12)))
            self.screen.blit(load_text, text_rect)

        # Draw Vehicles ("Pips") on Main Map
        for road in roads:
            for v in road._get_vehicles(Direction.FORWARD): self._draw_vehicle_pip(road, v, Direction.FORWARD, self.screen, is_zoomed=False)
            for v in road._get_vehicles(Direction.BACKWARD): self._draw_vehicle_pip(road, v, Direction.BACKWARD, self.screen, is_zoomed=False)

        # Draw vehicles held inside junctions on the main map
        for node in nodes:
            node_pos = self._map_coords(node.pos)
            if hasattr(node, 'current_vehicle') and node.current_vehicle is not None:
                v = node.current_vehicle
                color = getattr(v, 'color', self.color_veh)
                pygame.draw.circle(self.screen, color, node_pos, 4)
                pygame.draw.circle(self.screen, self.color_bg, node_pos, 4, 1)
            if hasattr(node, 'vehicles_in_circle'):
                for entry in node.vehicles_in_circle:
                    v = entry['veh']
                    progress = 1.0 - (entry['timer'] / entry['total_time'])
                    angle = entry['start_angle'] + (entry['end_angle'] - entry['start_angle']) * progress
                    dist = 9  # small ring radius on main map
                    vx = node_pos[0] + math.cos(angle) * dist
                    vy = node_pos[1] + math.sin(angle) * dist
                    color = getattr(v, 'color', self.color_veh)
                    pygame.draw.circle(self.screen, color, (int(vx), int(vy)), 4)
                    pygame.draw.circle(self.screen, self.color_bg, (int(vx), int(vy)), 4, 1)

        # Draw Nodes (Squares for ends, Circles for junctions)
        for node in nodes:
            if not node.pos: continue
            pos = self._map_coords(node.pos)
            node_type = node.__class__.__name__

            if "Source" in node_type:
                rect = pygame.Rect(0, 0, 18, 18); rect.center = pos
                pygame.draw.rect(self.screen, self.color_source, rect)
            elif "Sink" in node_type:
                rect = pygame.Rect(0, 0, 18, 18); rect.center = pos
                pygame.draw.rect(self.screen, getattr(node, 'color', self.color_sink), rect)
            else:
                # Standard Blue Circle for Junctions
                pygame.draw.circle(self.screen, self.color_junc, pos, 10)

            # Node Label
            lbl_node = self.font.render(node.node_id, True, self.color_text)
            self.screen.blit(lbl_node, (pos[0]-10, pos[1]-28))

        # =========================================================
        # 2. DRAW PICTURE-IN-PICTURE (PiP) ZOOM BOX
        # =========================================================
        if self.selected_node:
            self._render_zoom_box(self.selected_node, roads)

        # Draw Time indicator
        time_text = self.font_lg.render(f"Time: {t:.1f} s", True, (255,255,255))
        self.screen.blit(time_text, (20, 20))
        if not self.selected_node:
            instr = self.font.render("Click a junction to inspect internals", True, (150,150,150))
            self.screen.blit(instr, (20, 50))

        pygame.display.flip()

        if self.record_gif and Image is not None:
            raw_str = pygame.image.tostring(self.screen, "RGB")
            img = Image.frombytes("RGB", self.screen.get_size(), raw_str)
            self.frames.append(img)

    def _render_zoom_box(self, node, roads):
        """Renders the magnified PiP overlay box."""
        # Calculate box position (Top Right)
        margin = 20
        bx, by = self.width - self.zoom_box_size - margin, margin
        bw, bh = self.zoom_box_size, self.zoom_box_size
        
        # Setup local coordinate system for the box
        local_scale = self.scale * self.zoom_magnification
        # Calculate local offset so the SELECTED node is in the CENTER of the box
        local_ox = bx + (bw / 2) - (node.pos[0] * local_scale)
        local_oy = by + (bh / 2) - (node.pos[1] * local_scale)

        # 1. Draw Box Background & Border
        rect_box = pygame.Rect(bx, by, bw, bh)
        pygame.draw.rect(self.screen, self.color_ui_bg, rect_box)
        pygame.draw.rect(self.screen, (200, 200, 200), rect_box, 2) # Light gray border

        # Define clipping so drawing inside the box doesn't bleed out
        self.screen.set_clip(rect_box)

        # 2. Draw ROADS and VEHICLES connected to this node in high magnification
        for road in roads:
            if road.node_a == node or road.node_b == node:
                p1 = self._map_coords(road.node_a.pos, local_scale, local_ox, local_oy)
                p2 = self._map_coords(road.node_b.pos, local_scale, local_ox, local_oy)
                
                # --- NEW: Zoom Box Load Coloring ---
                fwd_load = len(road._get_vehicles(Direction.FORWARD))
                bwd_load = len(road._get_vehicles(Direction.BACKWARD))
                current_load = fwd_load + bwd_load
                max_load = getattr(road, 'capacity', 10)
                
                road_color = self.color_sink if current_load >= max_load else self.color_road
                
                # Draw thick local road
                pygame.draw.line(self.screen, road_color, p1, p2, 12)
                
                # --- NEW: Render Load Text in Zoom Box ---
                mid_x = (p1[0] + p2[0]) / 2
                mid_y = (p1[1] + p2[1]) / 2
                
                text_color = self.color_sink if current_load >= max_load else (255, 255, 255)
                load_text = self.font_lg.render(f"{current_load}/{max_load}", True, text_color)
                
                # Add a tiny background rect for the text inside the PIP so it doesn't get lost in pips
                text_rect = load_text.get_rect(center=(int(mid_x), int(mid_y - 25)))
                bg_rect = text_rect.inflate(6, 4)
                pygame.draw.rect(self.screen, self.color_bg, bg_rect, border_radius=3)
                self.screen.blit(load_text, text_rect)
                
                # Draw high-magnification "Pips" moving around
                for v in road._get_vehicles(Direction.FORWARD): 
                    self._draw_vehicle_pip(road, v, Direction.FORWARD, self.screen, local_scale, local_ox, local_oy, is_zoomed=True)
                for v in road._get_vehicles(Direction.BACKWARD): 
                    self._draw_vehicle_pip(road, v, Direction.BACKWARD, self.screen, local_scale, local_ox, local_oy, is_zoomed=True)

        # 3. Draw the focused node (Junction/Roundabout) in detail
        node_pos = self._map_coords(node.pos, local_scale, local_ox, local_oy)
        
        # Roundabout specific internal view (Smooth Movement)
        if hasattr(node, 'vehicles_in_circle'):
            # Draw the physical roundabout ring
            pygame.draw.circle(self.screen, self.color_road, node_pos, 35, 10)
            pygame.draw.circle(self.screen, self.color_junc, node_pos, 25)
            
            for entry in node.vehicles_in_circle:
                # Calculate progress (0.0 at entry, 1.0 at exit)
                progress = 1.0 - (entry['timer'] / entry['total_time'])
                
                # Interpolate the angle
                current_angle = entry['start_angle'] + (entry['end_angle'] - entry['start_angle']) * progress
                
                # Convert polar (angle/dist) to Cartesian (x/y)
                dist = 30 # Radius of the vehicle path in the roundabout
                vx = node_pos[0] + math.cos(current_angle) * dist
                vy = node_pos[1] + math.sin(current_angle) * dist
                
                # Draw the moving "pip"
                pygame.draw.circle(self.screen, getattr(entry['veh'], 'color', self.color_veh_pip), (int(vx), int(vy)), 6)
                pygame.draw.circle(self.screen, (0, 0, 0), (int(vx), int(vy)), 6, 1)
                
        # --- Traffic Signal Visuals (Inside the PiP Box) ---
        if hasattr(node, 'active_index') and not hasattr(node, 'vehicles_in_circle'):
            active_idx = node.active_index
            
            for i, (incoming_road, incoming_dir) in enumerate(node.incoming):
                # Calculate the point where the road meets the junction
                road_p1 = self._map_coords(incoming_road.node_a.pos, local_scale, local_ox, local_oy)
                road_p2 = self._map_coords(incoming_road.node_b.pos, local_scale, local_ox, local_oy)
                
                # Determine which end of the road is touching our node
                start_pt = road_p2 if incoming_road.node_b == node else road_p1
                end_pt = road_p1 if incoming_road.node_b == node else road_p2
                
                # Vector math to place the light at the entrance
                dx, dy = end_pt[0] - start_pt[0], end_pt[1] - start_pt[1]
                dist = math.hypot(dx, dy)
                if dist == 0: continue
                
                # Place the signal bar about 30 pixels out from the junction center
                signal_dist = 35 
                sx = node_pos[0] + (dx / dist) * signal_dist
                sy = node_pos[1] + (dy / dist) * signal_dist
                
                # Calculate the perpendicular vector for a "bar" look
                perp_x, perp_y = -dy / dist * 15, dx / dist * 15
                
                # Determine Color (Green for active, Red for others)
                is_green = (i == active_idx)
                sig_color = (46, 204, 113) if is_green else (192, 57, 43)
                
                # Draw the Signal Bar
                pygame.draw.line(self.screen, sig_color, 
                                 (sx - perp_x, sy - perp_y), 
                                 (sx + perp_x, sy + perp_y), 6)
                
                # Add a "Glow" for the green light
                if is_green:
                    glow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (46, 204, 113, 80), (20, 20), 20)
                    self.screen.blit(glow_surf, (sx - 20, sy - 20))

            # Draw the internal vehicle (the one currently 'crossing')
            if node.current_vehicle:
                pygame.draw.circle(self.screen, getattr(node.current_vehicle, 'color', self.color_veh_pip), node_pos, 10)
                pygame.draw.circle(self.screen, (0, 0, 0), node_pos, 10, 1)

        # Standard/Signal Junction specific internal view (Single vehicle hold)
        elif hasattr(node, 'current_vehicle') and node.current_vehicle is not None:
            pygame.draw.circle(self.screen, self.color_junc, node_pos, 25)
            # Draw the trapped vehicle as a yellow pip dead-center
            pygame.draw.circle(self.screen, getattr(node.current_vehicle, 'color', self.color_veh_pip), node_pos, 10)
        else:
            # Just draw the blue node
            pygame.draw.circle(self.screen, self.color_junc, node_pos, 25)

        # Label the node again inside the box (bigger text)
        lbl_box_node = self.font_lg.render(f"Inspecting: {node.node_id}", True, (255,255,255))
        self.screen.blit(lbl_box_node, (node_pos[0]-40, node_pos[1]-60))

        # Reset clipping
        self.screen.set_clip(None)

    def _draw_vehicle_pip(self, road, vehicle, direction, surface, scale=None, ox=None, oy=None, is_zoomed=False):
        """Calculates 'pip' (vehicle) coordinates and draws it to the specified surface."""
        # Local Coordinate lookup
        s = scale or self.scale
        tx = ox if ox is not None else self.offset_x
        ty = oy if oy is not None else self.offset_y

        start_pos = road.node_a.pos
        end_pos = road.node_b.pos
        if direction == Direction.BACKWARD: start_pos, end_pos = end_pos, start_pos

        dx = end_pos[0] - start_pos[0]; dy = end_pos[1] - start_pos[1]
        angle = math.atan2(dy, dx)
        # Normalize against stop_line so vehicles visually reach the junction node,
        # not freeze 5 units short of it.
        stop_line = road.length - road.stop_margin
        visible_length = stop_line if stop_line > 0 else road.length
        progress = max(0.0, min(1.0, vehicle.position / visible_length))
        sim_x, sim_y = start_pos[0] + (dx * progress), start_pos[1] + (dy * progress)

        # Standard map coordinate
        base_x, base_y = int(sim_x * s + tx), int(sim_y * s + ty)

        # Visual Tuning (Bigger pips and lane offsets inside the zoom box)
        if is_zoomed:
            veh_radius = 6
            lane_offset_mag = 7.0
            color_veh = getattr(vehicle, 'color', self.color_veh_pip) 
            color_border = (0, 0, 0)       
        else:
            veh_radius = 4
            lane_offset_mag = 4.0
            color_veh = getattr(vehicle, 'color', self.color_veh)     
            color_border = self.color_bg   

        # Apply lane offset normal to the road line
        nx = -math.sin(angle) * lane_offset_mag
        ny = math.cos(angle) * lane_offset_mag
        final_x, final_y = int(base_x + nx), int(base_y + ny)

        # DRAW PIP (Fill)
        pygame.draw.circle(surface, color_veh, (final_x, final_y), veh_radius)
        # DRAW BORDER (Essential for showing individual pips in queues)
        pygame.draw.circle(surface, color_border, (final_x, final_y), veh_radius, 1)

    def save_gif(self, filename="results/simulation.gif"):
        if not self.record_gif or not self.frames: return 
        if Image is None:
            print("Cannot save GIF: Pillow is not installed.")
            return
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        print(f"\nStitching {len(self.frames)} frames into GIF at {filename}...")
        self.frames[0].save(filename, save_all=True, append_images=self.frames[1:], duration=100, loop=0)
        print("GIF successfully saved!")
    