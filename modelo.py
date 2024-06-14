import agentpy as ap
import IPython
import random
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import heapq

# Definición del agente semáforo
class TrafficLight(ap.Agent):
    def setup(self):
        self.state = "red"  # Estados posibles: red, yellow, green
        self.timer = 0
        self.cycle = ["green", "yellow", "red"]
        self.neighbors = []  # Lista de vecinos

    def update(self, global_timer):
        # Cambiar el estado del semáforo basado en el temporizador global
        cycle_length = 26
        if self.state == "green" and global_timer % cycle_length == 10:
            self.state = "yellow"
        elif self.state == "yellow" and global_timer % cycle_length == 13:
            self.state = "red"
            self.sendMessage()
        elif self.state == "red" and global_timer % cycle_length == 0:
            pass  # Esperar a recibir mensaje

    def sendMessage(self):
        for neighbor in self.neighbors:
            neighbor.receiveMessage()

    def receiveMessage(self):
        self.state = "green"

# Heurística de A* (distancia de Manhattan)
def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

# Función de búsqueda A* mejorada
def a_star_search(grid, start, goal):
    if not (0 <= start[0] < grid.shape[0] and 0 <= start[1] < grid.shape[1]):
        raise ValueError(f"Start position out of bounds: {start}")
    if not (0 <= goal[0] < grid.shape[0] and 0 <= goal[1] < grid.shape[1]):
        raise ValueError(f"Goal position out of bounds: {goal}")
    
    if grid[goal[0]][goal[1]] == 0:
        raise ValueError(f"Goal position is not traversable: {goal}")

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

# Definición del agente vehículo mejorada
class Car(ap.Agent):
    def setup(self):
        self.velocity = 0  # Estacionario
        self.next = np.array([0, 0])  # Siguiente movimiento
        self.path = []  # Ruta calculada por A*
        self.trafficLight = None  # Semáforo asignado
        self.destination = None
        self.direction = None
        self.path = []
        self.neighbors = []  # Inicializar lista de vecinos

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
        self.velocity = 1  # Se recibe mensaje del semáforo para avanzar

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
                self.path.pop(0)  # Eliminar la posición alcanzada
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

# Definición del ambiente
class Environment(ap.Grid):
    def setup(self):
        self.traffic_lights = ap.AgentList(self.model, 4, TrafficLight)
        self.cars = ap.AgentList(self.model, 7, Car)  # Cambié el número de coches a 8
        self.add_agents(self.traffic_lights, [(3, 3), (9, 3), (9, 9), (2, 9)])

        car_positions = [(5, 3), (5, 2), (3, 7), (3,8), (7, 9), (7, 10), (9, 5), (10, 5)]
        car_directions = ['frente', 'frente', 'right', 'right', 'left', 'left', 'left', 'left']  # Añadí más direcciones
        self.add_agents(self.cars, car_positions)

        for car, direction in zip(self.cars, car_directions):
            car.direction = direction

        # Asignar semáforos a los coches basado en los sectores
        for car in self.cars:
            car.trafficLight = self.assign_traffic_light(car)

        # Definir vecinos para los semáforos (sentido de las manecillas del reloj)
        self.traffic_lights[0].neighbors.append(self.traffic_lights[1])
        self.traffic_lights[1].neighbors.append(self.traffic_lights[2])
        self.traffic_lights[2].neighbors.append(self.traffic_lights[3])
        self.traffic_lights[3].neighbors.append(self.traffic_lights[0])

    def assign_traffic_light(self, car):
        pos = self.positions[car]
        if pos[0] < 6 and pos[1] < 6:
            return self.traffic_lights[0]  # Sector 1 
        elif pos[0] < 6 and pos[1] >= 6:
            return self.traffic_lights[3]  # Sector 2
        elif pos[0] >= 6 and pos[1] < 6:
            return self.traffic_lights[1]  # Sector 3
        elif pos[0] >= 6 and pos[1] >= 6:
            return self.traffic_lights[2]  # Sector 4 

# Definición del modelo
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
        self.global_timer = 0  # Temporizador global

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
        pass  # Aquí puedes actualizar la lógica de recolección de datos o visualización

    def end(self):
        pass  # Aquí puedes manejar la lógica de finalización del modelo

# Función de animación personalizada
def animation_plot(model, ax):
    ax.clear()
    grid = model.grid
    grid_map = model.grid_map

    for x in range(grid_map.shape[0]):
        for y in range(grid_map.shape[1]):
            if grid_map[x, y] == 0:
                ax.add_patch(plt.Rectangle((y, x), 1, 1, color='dimgray'))  # No transitable
            elif grid_map[x, y] == 1:
                ax.add_patch(plt.Rectangle((y, x), 1, 1, color='lightgray'))  # Calle

    positions = [grid.positions[agent] for agent in grid.agents]

    colors = []
    for agent in grid.agents:
        if isinstance(agent, TrafficLight):
            if agent.state == "red":
                colors.append('red')
            elif agent.state == "yellow":
                colors.append('yellow')
            else:
                colors.append('green')
        else:
            colors.append('blue')

    x, y = zip(*positions)
    ax.scatter(y, x, c=colors, s=100, marker='s')  # 's' es para cuadros
    ax.set_xlim(-1, grid_map.shape[1])
    ax.set_ylim(-1, grid_map.shape[0])
    ax.set_xticks(range(grid_map.shape[1]))
    ax.set_yticks(range(grid_map.shape[0]))
    ax.grid(True)

# Ejecución del modelo
parameters = {
    'steps': 100
}

fig, ax = plt.subplots()
model = TrafficModel(parameters)
animation = ap.animate(model, fig, ax, animation_plot)
IPython.display.HTML(animation.to_jshtml())
