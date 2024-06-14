import asyncio
import json
import websockets
import agentpy as ap
import numpy as np

# Mapa
map_array = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
]

# Posiciones del alto (usando el formato (row, column))
stopsign_positions = [(1, 4)]

# Pos inicial
starting_position = (1, 0)

class CarAgent(ap.Agent):

    def setup(self):
        self.position = np.array(starting_position)
        self.velocity = np.array([0, 1])  # Mover a la derecha
        self.stop_counter = 0

    def update_velocity(self):
        # Parar en la señal de alto
        if tuple(self.position) == stopsign_positions[0]:
            if self.stop_counter < 3:
                self.stop_counter += 1
                return False  # Parar por 3 pasos
            else:
                self.stop_counter = 0
        return True

    def update_position(self):
        # Mover si no esta parado
        if self.update_velocity():
            new_position = self.position + self.velocity
            # Checar si se puede mover
            if self.is_valid_position(new_position):
                self.position = new_position

    def is_valid_position(self, pos):
        row, col = pos
        if row < 0 or row >= len(map_array) or col < 0 or col >= len(map_array[0]):
            return False
        return map_array[row][col] == 1

class IntersectionModel(ap.Model):

    def setup(self):
        self.car = CarAgent(self)
        self.agents = ap.AgentList(self, 1, CarAgent)
        self.agents[0].setup()  # Inicializar el agente del coche

    def step(self):
        self.agents.update_position()

# Parametros
parameters = {
    'steps': 20
}

async def send_initial_data(websocket):
    initial_data = {
        'map': map_array,
        'car_position': list(starting_position),
        'stopsign_positions': stopsign_positions
    }
    await websocket.send(json.dumps(initial_data))

async def send_position_update(websocket, position):
    update_data = {
        'car_position': position.tolist()
    }
    await websocket.send(json.dumps(update_data))

async def simulation_server(websocket, path):
    model = IntersectionModel(parameters)
    model.setup()

    await send_initial_data(websocket)

    for _ in range(parameters['steps']):
        model.step()
        car_position = model.agents[0].position.copy()
        await send_position_update(websocket, car_position)
        await asyncio.sleep(0.5)

start_server = websockets.serve(simulation_server, "localhost", 8765)

# Correr el servidor websocket y simulacion
asyncio.get_event_loop().run_until_complete(start_server)
print("WebSocket server started on ws://localhost:8765")
asyncio.get_event_loop().run_forever()
