import asyncio
import json
import websockets
import agentpy as ap
import numpy as np
import random

class TrafficLight(ap.Agent):
    def setup(self):
        self.state = "red"
        self.timer = 0
        self.cycle = ["green", "yellow", "red"]
        self.neighbors = []

    def update(self, global_timer):
        cycle_length = 26
        if self.state == "green" and global_timer % cycle_length == 10:
            self.state = "yellow"
        elif self.state == "yellow" and global_timer % cycle_length == 13:
            self.state = "red"
            self.sendMessage()
        elif self.state == "red" and global_timer % cycle_length == 0:
            pass

    def sendMessage(self):
        for neighbor in self.neighbors:
            neighbor.receiveMessage()

    def receiveMessage(self):
        self.state = "green"

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star_search(grid, start, goal):
    neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    close_set = set()
    came_from = {}
    gscore = {start: 0}
    fscore = {start: heuristic(start, goal)}
    oheap = []
    heapq.heappush(oheap, (fscore[start], start))

    while oheap:
        current = heapq.heappop(oheap)[1]

        if current == goal:
            data = []
            while current in came_from:
                data.append(current)
                current = came_from[current]
            data.append(start)
            data.reverse()
            return data

        close_set.add(current)
        for i, j in neighbors:
            neighbor = current[0] + i, current[1] + j
            tentative_g_score = gscore[current] + 1

            if 0 <= neighbor[0] < grid.shape[0] and 0 <= neighbor[1] < grid.shape[1]:
                if grid[neighbor[0]][neighbor[1]] == 0:
                    continue
            else:
                continue

            if neighbor in close_set and tentative_g_score >= gscore.get(neighbor, float('inf')):
                continue

            if tentative_g_score < gscore.get(neighbor, float('inf')) or neighbor not in [i[1] for i in oheap]:
                came_from[neighbor] = current
                gscore[neighbor] = tentative_g_score
                fscore[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                heapq.heappush(oheap, (fscore[neighbor], neighbor))

    return []

class Car(ap.Agent):
    def setup(self):
        self.velocity = 0
        self.next = np.array([0, 0])
        self.path = []
        self.trafficLight = None
        self.destination = None
        self.direction = None
        self.path = []
        self.neighbors = []

    def sendMessage(self):
        for neighbor in self.neighbors:
            neighbor.receiveMessage()

    def setDestino(self):
        self.destination = self.calcDestino(self.model.grid.positions[self], self.direction, self.model.grid_map)

    def calcDestino(self, posicion, direccion, grid):
        columna, fila = posicion
        destino = [columna, fila]
        if columna < 6 and fila < 6:
            destino = [columna, len(grid)-1]  
        elif columna < 6 and fila >= 6:
            destino = [len(grid)-1, fila]
        elif columna >= 6 and fila < 6:
            destino = [0, fila] 
        elif columna >= 6 and fila >= 6:
            destino = [columna, 0]

        while grid[destino[0]][destino[1]] == 0:
            if direccion == 'frente':
                destino[0] += 1 if columna < grid.shape[0] // 2 else -1
            elif direccion == 'left':
                destino[1] += 1
            elif direccion == 'right':
                destino[1] -= 1

        return destino

    def receiveMessage(self):
        self.velocity = 1

    def update(self):
        if self.destination is None:
            self.setDestino()
        if not self.path:
            try:
                path = a_star_search(self.model.grid_map, self.model.grid.positions[self], tuple(self.destination))
                if not path:
                    print(f"No se puede calcular la ruta para el coche {self}")
                else:
                    self.path = path
            except ValueError as e:
                print(e)
        
        if len(self.path) > 1:
            next_position = self.path[1]
            if self.trafficLight and self.trafficLight.state == "green" and not self.check_collision(next_position):
                self.model.grid.move_to(self, next_position)
                self.path.pop(0)
            elif self.check_collision(next_position):
                self.negotiate(next_position)

    def check_collision(self, position):
        for agent in self.model.grid.agents:
            if agent is not self and self.model.grid.positions[agent] == position:
                return agent
        return False

    def negotiate(self, position):
        other_car = self.check_collision(position)
        if other_car:
            my_distance = heuristic(self.model.grid.positions[self], self.destination)
            other_distance = heuristic(self.model.grid.positions[other_car], other_car.destination)
            if my_distance < other_distance:
                self.velocity = 1
                other_car.velocity = 0
            else:
                self.velocity = 0
                other_car.velocity = 1

class Environment(ap.Grid):
    def setup(self):
        self.traffic_lights = ap.AgentList(self.model, 4, TrafficLight)
        self.cars = ap.AgentList(self.model, 7, Car)
        self.add_agents(self.traffic_lights, [(3, 3), (9, 3), (9, 9), (2, 9)])

        car_positions = [(5, 3), (5, 2), (3, 7), (3,8), (7, 9), (7, 10), (9, 5), (10, 5)]
        car_directions = ['frente', 'frente', 'right', 'right', 'left', 'left', 'left', 'left']
        self.add_agents(self.cars, car_positions)

        for car, direction in zip(self.cars, car_directions):
            car.direction = direction

        for car in self.cars:
            car.trafficLight = self.assign_traffic_light(car)

        self.traffic_lights[0].neighbors.append(self.traffic_lights[1])
        self.traffic_lights[1].neighbors.append(self.traffic_lights[2])
        self.traffic_lights[2].neighbors.append(self.traffic_lights[3])
        self.traffic_lights[3].neighbors.append(self.traffic_lights[0])

    def assign_traffic_light(self, car):
        pos = self.positions[car]
        if pos[0] < 6 and pos[1] < 6:
            return self.traffic_lights[0]
        elif pos[0] < 6 and pos[1] >= 6:
            return self.traffic_lights[3]
        elif pos[0] >= 6 and pos[1] < 6:
            return self.traffic_lights[1]
        elif pos[0] >= 6 and pos[1] >= 6:
            return self.traffic_lights[2]

class TrafficModel(ap.Model):
    def setup(self):
        self.grid_map = np.array([
            [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0],
        ])
        self.grid = ap.Grid(self, (self.grid_map.shape[0], self.grid_map.shape[1]), torus=False)
        self.environment = Environment(self, (self.grid_map.shape[0], self.grid_map.shape[1]), torus=False)
        self.traffic_lights = self.environment.traffic_lights
        self.cars = self.environment.cars
        self.global_timer = 0

        self.grid.add_agents(self.traffic_lights, positions=[(3, 3), (9, 3), (9, 9), (3, 9)])
        self.grid.add_agents(self.cars, positions=[(5, 3), (5, 2), (3, 7), (3,8), (7, 9), (7, 10), (9, 5), (10, 5)])

        initial_green_light = random.choice(self.traffic_lights)
        initial_green_light.state = "green"

    def step(self):
        self.global_timer += 1
        for traffic_light in self.traffic_lights:
            traffic_light.update(self.global_timer)
        for car in self.cars:
            car.update()

    def update(self):
        pass

    def end(self):
        pass

async def send_initial_data(websocket, model):
    data = {
        'map': model.grid_map.tolist(),
        'traffic_lights': [{'position': model.grid.positions[tl], 'state': tl.state} for tl in model.traffic_lights],
        'cars': [{'position': model.grid.positions[car]} for car in model.cars]
    }
    await websocket.send(json.dumps(data))

async def send_position_update(websocket, model):
    data = {
        'traffic_lights': [{'position': model.grid.positions[tl], 'state': tl.state} for tl in model.traffic_lights],
        'cars': [{'position': model.grid.positions[car]} for car in model.cars]
    }
    await websocket.send(json.dumps(data))

async def simulation_server(websocket, path):
    model = TrafficModel()
    model.setup()

    await send_initial_data(websocket, model)

    for _ in range(100):  # Número de pasos de simulación
        model.step()
        await send_position_update(websocket, model)
        await asyncio.sleep(0.1)

start_server = websockets.serve(simulation_server, "localhost", 8765)

# Run the WebSocket server
asyncio.get_event_loop().run_until_complete(start_server)
print("WebSocket server started on ws://localhost:8765")
asyncio.get_event_loop().run_forever()
