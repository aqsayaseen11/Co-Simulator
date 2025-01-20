from flask import Flask, jsonify, request, render_template
from libcosimpy.CosimExecution import CosimExecution
from libcosimpy.CosimObserver import CosimObserver
from libcosimpy.CosimManipulator import CosimManipulator
import os
import csv
import argparse
import time
import requests
import subprocess
import socket
import json


import logging
#disable request logging in console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# Global variables for execution, observer, manipulator
execution = None
observer = None
time_series_observer = None  # Time series observer for tracking all variables
manipulator = None
logical_simulation_time = 0.0  # Start logical simulation time at 0 seconds
simulation_running = False


# Parse command-line arguments
parser = argparse.ArgumentParser(description="Run the Flask app with simulation parameters.")
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host IP address for the Flask server')
parser.add_argument('--port', type=int, default=5000, help='Port for the Flask server')
args = parser.parse_args()


previous_waypoints = {
    'x_wp': None,
    'y_wp': None,
    'psi_wp': None,
    'x_tp': None,
    'y_tp': None,
    'psi_tp': None
}

variables_id = {
    'x_wp': 31,
    'y_wp': 33,
    'psi_wp': 29,
    'x_tp': 30,
    'y_tp': 32,
    'psi_tp': 28,
    'x_ref': 38,
    'y_ref': 39,
    'psi_ref': 37,
    'x_act': 49,
    'y_act': 51,
    'psi_act': 44
}

slave_index_id = {
    'reference_generator': 4,
    'dp_controller': 2
}

# TODO start_plot can be replaced with server status when becomes available
start_plot=False

simulation_server_info = []

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/deploy', methods=['POST'])
def deploy_simulation_server():
    global simulation_server_info
    data = request.get_json()
    simulation_server_info = data.get('servers', [])
    print('CONT.DEPLOY: Simulation Server Info: ', simulation_server_info)
    for sim in simulation_server_info:
        ip = sim.get('ip')
        port = sim.get('port')
        id = sim.get('id')

        try:
            print('CONT.DEPLOY: Starting server', id)
            # Check if the port is available
            process=subprocess.Popen(["python", "src/simulator.py", "--host", ip, "--port", port, "--sid", id], shell=True, env=os.environ)

            
            # Wait for a brief moment to ensure the server starts
            time.sleep(5)
            pid = process.pid
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500 
    return jsonify({'message': f'Server(s) deployed','servers':simulation_server_info, 'PID': pid}), 200

@app.route('/plot_data', methods=['GET'])
def plot_values():
    global observer, time_series_observer, logical_simulation_time, execution, simulation_server_info

    plot_values=[]
    #print('simulation_server_info: ',simulation_server_info)
    for sim in simulation_server_info:
        ip = sim['ip']
        port =sim['port']
        #print('IP Add: ',ip, 'Port Number: ',port)
        
        # Form the base URL for the current simulation server
        base_url = f"http://{ip}:{port}/"
        #print('Getting Reference Values: ',base_url + 'get_data')
        try:
            # Send the request to initialize the simulation
            response = requests.get(base_url + 'get_data')
            
            # Check if the request was successful
            if response.status_code == 200:
                #print(f"Successfully received values from simulation server {ip}:{port}")
                #print("Get_Data Response:", response.json())  # Print the JSON response
                plot_values.append(response.json())
            else:
                #print(f"Failed to start simulation for server {ip}:{port}")
                #print("Response code:", response.status_code)
                #print("Response:", response.text)
                pass
                
        except requests.exceptions.RequestException as e:
            # Handle any exceptions that occur during the request
            # print(f"Error connecting to simulation server {ip}:{port}: {e}")
            pass

    return jsonify(plot_values)


if __name__ == '__main__':
    app.run(host=args.host, port=args.port)
