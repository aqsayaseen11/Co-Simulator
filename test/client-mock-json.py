from flask import jsonify
import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

# process=subprocess.Popen(["python", "simulation_controller.py"])

# Function to deploy the sim server
def deploy(BASE_URL, simulation_server_info):
    try:
        # Send the request to initialize the simulation
        print('SIM INFO: ',simulation_server_info)
        response = requests.post(f"{BASE_URL}/deploy", json=simulation_server_info)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Simulation server(s) deployed successfully")
            print("Response:", response.json())  # Print the JSON response
        else:
            print(f"Failed to deploy Simulation server(s)")
            print("Response code:", response.status_code)
            print("Response:", response.text)

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to simulation server(s): {e}")

#Function to run the sim server
def init_simulation(simulation_server_info):
    response = ''
    simulation_time_step=1
    real_time_factor_target=1.0
    steps_to_monitor=5 
    #execution_step_value=25
    info={'real_time_factor_target':real_time_factor_target,'steps_to_monitor':steps_to_monitor}
    time.sleep(10)

    try:
        ip = simulation_server_info['ip']
        port =simulation_server_info['port']
        print('IP Add: ',ip, 'Port Number: ',port)       
        # Form the base URL for the current simulation server
        base_url = f"http://{ip}:{port}"
        # Send the request to initialize the simulation
        response = requests.post(f"{base_url}/init", json={"body": info})

        # Check if the request was successful
        if response.status_code == 200:
            print("Simulation initialized successfully")
            print("Response:", response.json())  # Print the JSON response
            return response.json()  # Corrected to call the method
        else:
            print(f"Failed to initialize simulation")
            print("Response code:", response.status_code)
            print("Response:", response.text)
            return response.text

    except requests.exceptions.RequestException as e:
        # Handle any exceptions that occur during the request
        print(f"Error connecting to simulation server: {e}")

        return None


# Function to get waypoints for a specific time
def get_waypoints_for_time(requested_time, previous_waypoint, events):
    matching_events = {}
    waypoint_found = False

    print(f"[DEBUG] Requested time (s): {requested_time}")  # Log requested time

    for event in events:
        event_time = event["time"]  # Event time is assumed to be in seconds

        print(f"[DEBUG] Checking event at {event_time} s (variable: {event['variable']}, value: {event['value']})")

        # Check if the requested time matches the event time exactly
        if int(requested_time)+1 == int(event_time):
            matching_events[event["variable"]] = event["value"]
            waypoint_found = True
            print(f"[DEBUG] Exact match: Waypoint found {matching_events} for event at time {event_time} s.")

    if waypoint_found:
        print('WAY POINT_MATCHED')
        return matching_events
    else:
        return None

def simulate(info,simulation_server_info):
        
    ip = simulation_server_info['ip']
    port =simulation_server_info['port']
    print('IP Add: ',ip, 'Port Number: ',port)
    # Form the base URL for the current simulation server
    base_url = f"http://{ip}:{port}"

    
    if int(port) == 5001:
        file='clients/scenerios/waypoints.json'
    else:
        file='clients/scenerios/waypoints1.json'
    # Load waypoints from the provided JSON file (the client(cvt) reads the scenario)
    with open(file) as f:
        waypoint_data = json.load(f)
        events = waypoint_data["events"]
    print('Loaded Waypoint File Name: ',file,' for Port: ',port)

    previous_waypoint = None  # Store the last known waypoint (initially set to None)

    if info and 'data' in info:
        current_simulation_time = info['data']['time']
        print(f"Current simulation time: {current_simulation_time}")
    else:
        print("Failed to retrieve simulation time")

    step = 0  # Step is equal to seconds that start from step 0
    num_steps = 6000 #simulation end time in sec
    #Fetching Waypoints.
    while step <= num_steps:

        waypoints = get_waypoints_for_time(current_simulation_time, previous_waypoint, events)
        if (waypoints is not None):
            # 1. Send request to server for the current simulation time and waypoints
            response = requests.post(f"{base_url}/next_wp", json={"time": current_simulation_time, "waypoints": waypoints, "simulation_server_info": simulation_server_info})
            
            if response.status_code == 200:
                print(f"[DEBUG] Client: Waypoints sent successfully at time {current_simulation_time}.")
            else:
                print(f"Error: Unable to send waypoints to server, status code: {response.status_code}")

        ref_response = requests.get(f"{base_url}/current_pos")
        if ref_response.status_code == 200:
            ref_values = ref_response.json()
            current_simulation_time= ref_values['time']

            # Print the received reference and actual values
            print(f"[DEBUG] Client: Received reference values:")
            print('Current Time: ',ref_values['time'])
            print(f"  Actual Values -> x_act: {ref_values['x_act']}, y_act: {ref_values['y_act']}, psi_act: {ref_values['psi_act']}, fuel: {ref_values['fuel']}")

        else:
            # Print an error message if the response code indicates failure
            print(f"[ERROR] Failed to fetch reference data. Status code: {ref_response.status_code}")

        # Add a delay to simulate real-time passage of time
        time.sleep(1)  # Wait for 1 second before proceeding to the next step

        # Increment simulation step
        step += 1

# Function to get the current simulation time from the server
def stop_simulation(base_url):
    for sim in simulation_server_info:
        ip = sim['ip']
        port =sim['port']
        print('IP Add: ',ip, 'Port Number: ',port)
        # Form the base URL for the current simulation server
        base_url = f"http://{ip}:{port}"
        response = requests.get(f"{base_url}/stop_simulation")
        if response.status_code == 200:
            data = response.json()
            server_time = data.get('time', 0.0)
            print(f"Simulation Stopped")  # Debug log to confirm the time
            return server_time
        else:
            print(f"Error: Could not retrieve server time, status code: {response.status_code}")
            return 0.0
    

def run_simulation(sim):
    # Initialize and start the simulation for each server
    info = init_simulation(sim)
    # Run the simulation in a loop and send waypoints as needed
    simulate(info, sim)
    # Stop the simulations after completion
    stop_simulation(simulation_server_info)

if __name__ == "__main__":
    # List of simulation servers
    simulation_server_info = { 
    "servers": [
        {"id": "0", "ip": "127.0.0.1", "port": "5001"},
        {"id": "1", "ip": "127.0.0.1", "port": "5002"}
    ]
    }

    # Base URL for simulation controller
    BASE_URL = "http://127.0.0.1:5000"

    # Start the Simulation Servers via controller by passing BASE_URL and simulation server info
    deploy(BASE_URL, simulation_server_info)

    # Use ThreadPoolExecutor to run each simulation concurrently
    with ThreadPoolExecutor(max_workers=len(simulation_server_info["servers"])) as executor:
        futures = [executor.submit(run_simulation, sim) for sim in simulation_server_info["servers"]]
        
        # Wait for all simulations to complete
        for future in futures:
            future.result()  # This will raise any exceptions from the threads if they occur


    print("[DEBUG] Client: Completed all simulation steps.")