import socket
import json
import random
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import signal
import pandas as pd
import sys
import os

# --- Constants ---
MAX_VEHICLES = 5
RED_LIGHT_DURATION = 10
GREEN_LIGHT_DURATION = 15
YELLOW_LIGHT_DURATION = 5
LOG_FILE = 'traffic_data_log.json'

# --- Traffic Light Control Logic ---
class TrafficLight:
    def __init__(self, intersection_name):
        self.state = "RED"  # Initial state is red
        self.name = intersection_name
        self.green_duration = GREEN_LIGHT_DURATION
        self.red_duration = RED_LIGHT_DURATION
        self.yellow_duration = YELLOW_LIGHT_DURATION
        self.vehicle_count_history = []

    def switch_to_green(self):
        """Switch the traffic light to green."""
        self.state = "GREEN"
        print(f"{self.name} Traffic Light is now GREEN.")
        self.log_traffic_data()

    def switch_to_red(self):
        """Switch the traffic light to red."""
        self.state = "RED"
        print(f"{self.name} Traffic Light is now RED.")
        self.log_traffic_data()

    def switch_to_yellow(self):
        """Switch the traffic light to yellow."""
        self.state = "YELLOW"
        print(f"{self.name} Traffic Light is now YELLOW.")
        self.log_traffic_data()

    def log_traffic_data(self):
        """Log traffic data to a JSON file."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = {
            'intersection': self.name,
            'state': self.state,
            'timestamp': timestamp,
            'vehicle_count': len(self.vehicle_count_history)
        }

        with open(LOG_FILE, 'a') as file:
            json.dump(log_entry, file)
            file.write("\n")
        print(f"Logged Data: {log_entry}")

    def update_vehicle_count(self, count):
        """Update the count of vehicles for the intersection."""
        self.vehicle_count_history.append(count)

    def get_vehicle_count(self):
        """Get current vehicle count."""
        return len(self.vehicle_count_history)


# --- Sensor Data Simulation (Multiple sensors) ---
class Sensor:
    def __init__(self, intersection_name):
        self.intersection_name = intersection_name
        self.vehicle_count = 0

    def generate_sensor_data(self):
        """Simulate the data sent by a traffic sensor."""
        self.vehicle_count = random.randint(0, MAX_VEHICLES)
        data = {'intersection': self.intersection_name, 'vehicle_count': self.vehicle_count}
        return data


# --- Traffic Controller: Decision Making based on Traffic Patterns ---
class TrafficController:
    def __init__(self):
        self.intersections = {
            "Intersection 1": TrafficLight("Intersection 1"),
            "Intersection 2": TrafficLight("Intersection 2"),
            "Intersection 3": TrafficLight("Intersection 3")
        }
        self.iterations = 10
        self.active_intersections = {}

    def manage_traffic(self):
        """Decide the traffic light states based on vehicle count."""
        iteration_count = 0
        intersection_data = {}
        while iteration_count < self.iterations:
            for intersection_name, traffic_light in self.intersections.items():
                vehicle_count = random.randint(0, MAX_VEHICLES)
                traffic_light.update_vehicle_count(vehicle_count)

                print(f"Checking Traffic for {intersection_name}: {vehicle_count} vehicles")

                if vehicle_count > 60:
                    traffic_light.switch_to_green()
                    time.sleep(traffic_light.green_duration)
                elif vehicle_count == 0:
                    traffic_light.switch_to_red()
                    time.sleep(traffic_light.red_duration)
                else:
                    traffic_light.switch_to_yellow()
                    time.sleep(traffic_light.yellow_duration)

                # Collect data for visualization
                intersection_data[intersection_name] = vehicle_count

            iteration_count += 1
            print(f"Iteration {iteration_count}/{self.iterations} completed.")

        return intersection_data

# --- Traffic System and Server ---
class TrafficSystem:
    def __init__(self, stop_event):
        self.sensor_1 = Sensor("Intersection 1")
        self.sensor_2 = Sensor("Intersection 2")
        self.sensor_3 = Sensor("Intersection 3")
        self.controller = TrafficController()
        self.active_intersections = {
            "Intersection 1": True,
            "Intersection 2": True,
            "Intersection 3": True
        }
        self.stop_event = stop_event
        
        # Initialize network traffic data dictionary
        self.network_traffic = {
            'timestamps': [],
            'vehicle_counts': []
        }

    def start_sensors(self):
        """Simulate traffic sensors sending data to the server."""
        while not self.stop_event.is_set():  # Check for stop event
            data_1 = self.sensor_1.generate_sensor_data()
            data_2 = self.sensor_2.generate_sensor_data()
            data_3 = self.sensor_3.generate_sensor_data()

            # Add timestamp and vehicle count to the network_traffic
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.network_traffic['timestamps'].append(current_timestamp)
            self.network_traffic['vehicle_counts'].append(data_1['vehicle_count'])
            self.network_traffic['vehicle_counts'].append(data_2['vehicle_count'])
            self.network_traffic['vehicle_counts'].append(data_3['vehicle_count'])

            # Simulate sending data to the server
            self.send_data_to_server(data_1)
            self.send_data_to_server(data_2)
            self.send_data_to_server(data_3)

            time.sleep(5)  # Wait for 5 seconds before sending new data

    def send_data_to_server(self, data):
        """Send sensor data to the server for processing."""
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect(('localhost', 12345))
            client.send(json.dumps(data).encode())
        except Exception as e:
            print(f"Error sending data to server: {e}")
        finally:
            client.close()
            
class Server:
    def __init__(self, stop_event):
        self.traffic_controller = TrafficController()
        self.stop_event = stop_event

    def start_server(self):
        """Start server to receive and process data."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.bind(('localhost', 12345))
            server.listen(5)
            print("Server listening on port 12345...")
        except Exception as e:
            print(f"Error starting server: {e}")
            return

        while not self.stop_event.is_set():  # Check for stop event
            try:
                server.settimeout(1)  # Allow timeout to exit the loop
                client_socket, client_address = server.accept()
                data = client_socket.recv(1024).decode()

                if data:
                    traffic_data = json.loads(data)
                    intersection_name = traffic_data['intersection']
                    vehicle_count = traffic_data['vehicle_count']
                    print(f"Received data from {intersection_name}: {vehicle_count} vehicles")

                    # Decide on the light state based on traffic data
                    self.traffic_controller.manage_traffic()

            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error while processing request: {e}")
            finally:
                client_socket.close()

        server.close()


# --- Simulation Setup: Threading for Sensor Data Generation ---
def run_traffic_system():
    """Start all components in separate threads."""
    stop_event = threading.Event()

    traffic_system = TrafficSystem(stop_event)
    sensor_thread = threading.Thread(target=traffic_system.start_sensors)
    sensor_thread.daemon = True
    sensor_thread.start()

    server = Server(stop_event)
    server_thread = threading.Thread(target=server.start_server)
    server_thread.daemon = True
    server_thread.start()

    # Let the system run for 10 iterations
    intersection_data = traffic_system.controller.manage_traffic()

    stop_event.set()  # Signal threads to stop
    sensor_thread.join()
    server_thread.join()

    print("Traffic system simulation ended.")

    # Plotting the results
    plot_traffic_flow(intersection_data)
    plot_traffic_light_state(traffic_system.controller.intersections)
    plot_network_traffic(traffic_system.network_traffic)

# --- Plotting Functions ---
def plot_traffic_flow(intersection_data):
    """Plot vehicle counts per intersection over time using Matplotlib."""
    intersections = list(intersection_data.keys())
    vehicle_counts = [intersection_data[intersection] for intersection in intersections]
    
    plt.figure(figsize=(10, 6))
    plt.bar(intersections, vehicle_counts, color='blue')
    plt.title('Vehicle Counts at Intersections')
    plt.xlabel('Intersection')
    plt.ylabel('Number of Vehicles')
    plt.show()

def plot_traffic_light_state(intersections):
    """Plot the traffic light states over time using Plotly."""
    traffic_light_states = {intersection.name: intersection.state for intersection in intersections.values()}
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=list(traffic_light_states.keys()), y=list(traffic_light_states.values())))
    fig.update_layout(title="Traffic Light States", xaxis_title="Intersection", yaxis_title="State")
    fig.show()

def plot_network_traffic(traffic_data):
    """Plot network traffic between sensors and server using Plotly."""
    timestamps = traffic_data['timestamps']
    vehicle_counts = traffic_data['vehicle_counts']

    # Create a line plot for network traffic
    fig = go.Figure(data=[go.Scatter(x=timestamps, y=vehicle_counts, mode='lines+markers', name='Sensor to Server Traffic')])
    fig.update_layout(title='Network Traffic Flow',
                      xaxis_title='Time',
                      yaxis_title='Vehicle Count')
    fig.show()


if __name__ == "__main__":
    run_traffic_system()
