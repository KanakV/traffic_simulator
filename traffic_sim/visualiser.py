import pygame
import math
try:
    from PIL import Image
except ImportError:
    Image = None

class Visualiser:
    def __init__(self, record_gif=False):
        pygame.init()
        
        # 1. Expand window size to occupy most of the screen
        # You can also pass pygame.FULLSCREEN flag if you want it completely borderless
        info_object = pygame.display.Info()
        self.width = int(info_object.current_w * 0.8)
        self.height = int(info_object.current_h * 0.8)
        
        # Fallback for headless environments
        if self.width < 100 or self.height < 100:
            self.width, self.height = 1280, 720
            
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Traffic Simulator")
        
        # -----------------------------
        # Minimalist Flat Palette
        # -----------------------------
        self.color_bg = (30, 34, 40)          # Deep Charcoal
        self.color_road = (80, 85, 95)        # Muted Slate
        self.color_source = (46, 204, 113)    # Emerald Green
        self.color_sink = (231, 76, 60)       # Alizarin Red
        self.color_junc = (52, 152, 219)      # Peter River Blue
        self.color_veh = (236, 240, 241)      # Cloud White
        self.color_veh_junc = (241, 196, 15)  # Sunflower Yellow
        self.color_text = (189, 195, 199)     # Silver
        self.color_text_node = (255, 255, 255)# Pure White

        self.font = pygame.font.SysFont("segoeui, arial, sans-serif", 16)
        self.font_large = pygame.font.SysFont("segoeui, arial, sans-serif", 20, bold=True)
        
        # Camera & Scaling
        self.camera_initialized = False
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.record_gif = record_gif
        self.frames = []

    def _init_camera(self, nodes):
        """Calculates scaling and offset to make the network fill the screen."""
        if not nodes:
            return
            
        # Find the bounding box of the entire network
        min_x = min(n.pos[0] for n in nodes if n.pos)
        max_x = max(n.pos[0] for n in nodes if n.pos)
        min_y = min(n.pos[1] for n in nodes if n.pos)
        max_y = max(n.pos[1] for n in nodes if n.pos)

        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)

        # Scale network to take up 80% of the available window space
        scale_x = (self.width * 0.8) / span_x
        scale_y = (self.height * 0.8) / span_y
        
        # Keep aspect ratio uniform
        self.scale = min(scale_x, scale_y)

        # Find the center of the network in simulation coordinates
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Calculate the offset needed to put the network center in the screen center
        self.offset_x = (self.width / 2) - (center_x * self.scale)
        self.offset_y = (self.height / 2) - (center_y * self.scale)
        
        self.camera_initialized = True

    def _map_coords(self, pos):
        """Scales and shifts simulation coordinates to screen pixels."""
        return (
            int(pos[0] * self.scale + self.offset_x), 
            int(pos[1] * self.scale + self.offset_y)
        )

    def render(self, nodes, roads, t):
        if not self.camera_initialized:
            self._init_camera(nodes)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

        self.screen.fill(self.color_bg)

        # Dynamic Sizing based on zoom scale
        road_thickness = max(4, int(6 * (self.scale / 10)))
        node_radius = max(10, int(12 * (self.scale / 15)))
        rect_size = max(16, int(20 * (self.scale / 15)))

        # 1. Draw Roads & Labels
        for road in roads:
            start_pos = self._map_coords(road.node_a.pos)
            end_pos = self._map_coords(road.node_b.pos)
            
            pygame.draw.line(self.screen, self.color_road, start_pos, end_pos, road_thickness)

            mid_x = (start_pos[0] + end_pos[0]) // 2
            mid_y = (start_pos[1] + end_pos[1]) // 2
            
            lbl_road = self.font.render(road.road_id, True, self.color_text)
            self.screen.blit(lbl_road, (mid_x + 8, mid_y + 8))

        # 2. Draw Vehicles
        from traffic_sim.direction import Direction
        for road in roads:
            for v in road._get_vehicles(Direction.FORWARD):
                self._draw_vehicle(road, v, Direction.FORWARD)
            for v in road._get_vehicles(Direction.BACKWARD):
                self._draw_vehicle(road, v, Direction.BACKWARD)

        # 3. Draw Nodes & Labels
        for node in nodes:
            if not node.pos: continue
            pos = self._map_coords(node.pos)

            node_type = node.__class__.__name__
            
            if "Source" in node_type:
                rect = pygame.Rect(0, 0, rect_size, rect_size)
                rect.center = pos
                pygame.draw.rect(self.screen, self.color_source, rect)
            elif "Sink" in node_type:
                rect = pygame.Rect(0, 0, rect_size, rect_size)
                rect.center = pos
                pygame.draw.rect(self.screen, self.color_sink, rect)
            else:
                pygame.draw.circle(self.screen, self.color_junc, pos, node_radius)
                
                if hasattr(node, 'current_vehicle') and node.current_vehicle is not None:
                    pygame.draw.circle(self.screen, self.color_veh_junc, pos, max(4, node_radius//2))

            lbl_node = self.font_large.render(node.node_id, True, self.color_text_node)
            lbl_rect = lbl_node.get_rect(center=(pos[0], pos[1] - (node_radius + 15)))
            self.screen.blit(lbl_node, lbl_rect)

        # 4. Draw UI
        time_text = self.font_large.render(f"Time: {t:.1f} s", True, self.color_text_node)
        self.screen.blit(time_text, (20, 20))

        pygame.display.flip()

        if self.record_gif and Image is not None:
            raw_str = pygame.image.tostring(self.screen, "RGB")
            size = self.screen.get_size()
            img = Image.frombytes("RGB", size, raw_str)
            self.frames.append(img)

    def _draw_vehicle(self, road, vehicle, direction):
        start_pos = road.node_a.pos
        end_pos = road.node_b.pos
        
        if direction == 1: # BACKWARD
            start_pos, end_pos = end_pos, start_pos

        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        angle = math.atan2(dy, dx)

        progress = max(0.0, min(1.0, vehicle.position / road.length))

        sim_x = start_pos[0] + (dx * progress)
        sim_y = start_pos[1] + (dy * progress)

        screen_pos = self._map_coords((sim_x, sim_y))
        
        # Offset vehicle to its respective lane
        offset_mag = max(3.0, 5.0 * (self.scale / 15))
        nx = -math.sin(angle) * offset_mag
        ny = math.cos(angle) * offset_mag
        
        final_x = int(screen_pos[0] + nx)
        final_y = int(screen_pos[1] + ny)

        # Size of the vehicle
        veh_radius = max(3, int(5 * (self.scale / 15)))

        # DRAW VEHICLE (White inner circle)
        pygame.draw.circle(self.screen, self.color_veh, (final_x, final_y), veh_radius)
        
        # DRAW OUTLINE (Dark border)
        # This makes queued cars look like distinct entities instead of a solid line
        pygame.draw.circle(self.screen, self.color_bg, (final_x, final_y), veh_radius, 2)

    def save_gif(self, filename="results/simulation.gif"):
        if not self.record_gif or not self.frames:
            return 
        if Image is None:
            print("Cannot save GIF: Pillow is not installed.")
            return
            
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        print(f"\nSaving minimalist GIF to {filename}...")
        self.frames[0].save(
            filename, 
            save_all=True, 
            append_images=self.frames[1:], 
            duration=100, 
            loop=0
        )
        print("GIF successfully saved!")

