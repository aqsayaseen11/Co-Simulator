from flask import jsonify
import requests
import time

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

# Function to run the sim server
def init_simulation(simulation_server_info):
    real_time_factor_target = 1.0
    steps_to_monitor = 5
    info = {'real_time_factor_target': real_time_factor_target, 'steps_to_monitor': steps_to_monitor}
    time.sleep(10)
    
    responses = {}
    try:
        for sim in simulation_server_info["servers"]:
            ip = sim['ip']
            port = sim['port']
            id = sim['id']

            print('INITIALIZING: IP Add:', ip, 'Port Number:', port, 'ID: ')
            base_url = f"http://{ip}:{port}"
            response = requests.post(f"{base_url}/init", json={"body": info})

            
            if response.status_code == 200:
                print("Simulation initialized successfully")
                responses[id] = response.json()
            else:
                print(f"Failed to initialize simulation")
                print("Response code:", response.status_code)
                print("Response:", response.text)
                responses[id] = response.json()
        return responses

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to simulation server: {e}")
        return None
    
#to get waypoints for the current time
def get_waypoints_for_time(current_simulation_time, sim_data):
    matched_waypoints = {ship["id"]: {} for ship in sim_data["ships"]}
    for ship in sim_data["ships"]:
        for event in ship["events"]:
            if int(current_simulation_time) == int(event["time"]):
                matched_waypoints[ship["id"]][event["variable"]] = event["value"]
                print(f"[DEBUG] Waypoint matched for ship {ship['id']} at time {event['time']} with {event['variable']} = {event['value']}")
    return matched_waypoints

#to send wp
def send_wp(waypoints, base_url, current_simulation_time):
    response = requests.post(f"{base_url}/next_wp", json={"time": current_simulation_time, "waypoints": waypoints})
    if response.status_code == 200:
        print(f"[DEBUG] Client: Waypoints sent successfully at time {current_simulation_time}.")
    else:
        print(f"Error: Unable to send waypoints to server, status code: {response.status_code}")
    return response.status_code


#to get actual position
def get_curr_pos(base_url):
    ref_response = requests.get(f"{base_url}/current_pos")
    if ref_response.status_code == 200:
        ref_values = ref_response.json()
        return ref_values
    else:
        print(f"[ERROR] Failed to fetch reference data. Status code: {ref_response.status_code}")
        return None

def calculate_next(curr_pos):
    # Using the first ship's time as the current simulation time 
    ship_time = list(curr_pos.keys())[0]
    current_simulation_time = curr_pos[ship_time]['time']  # Using the first available time
    print('Current Simulation Time: ',current_simulation_time)

    sim_data = {
        'ships': [
            {"id": "0",  
             "events": [
                {"time": 50, "variable": "x_wp", "value": 20.0},
                {"time": 50, "variable": "x_tp", "value": 250.0},
                {"time": 70, "variable": "x_wp", "value": 40.0},
                {"time": 70, "variable": "x_tp", "value": 50.0},
            ]},
            {"id": "1",
             "events": [
                {"time": 100, "variable": "psi_wp", "value": 1.507},
                {"time": 100, "variable": "psi_tp", "value": 750.0},
                {"time": 120, "variable": "y_wp", "value": 20.0},
                {"time": 120, "variable": "y_tp", "value": 1050.0},
            ]}
        ]
    }

    #to get matched waypoints based on the current simulation time
    matched_waypoints = get_waypoints_for_time(current_simulation_time, sim_data)
    return matched_waypoints


def simulate(simulation_server_info, i=0, end_second=6000):
    cur_pos = {}
    # i  is second that is equal to 25 steps in osp simulation environment. We are running simulation manually 25 steps by 25.

    while i <= end_second:
        for ship in simulation_server_info["servers"]:
            ship_url = f"http://{ship['ip']}:{ship['port']}"
            cur_pos[ship["id"]] = get_curr_pos(ship_url)
        
        #calculate next points for all ships
        next_wp = calculate_next(curr_pos=cur_pos)
        print('Current Pos: ',cur_pos)
        #send WP to all ships
        for ship in simulation_server_info["servers"]:
            ship_url = "http://" + ship["ip"] + ":" + ship["port"]
            if next_wp[ship["id"]]:
                send_wp(next_wp[ship["id"]], ship_url, cur_pos[ship["id"]]['time'])
        
        #time.sleep(1)  # Simulate real-time passage
        #Loop after 1 second
        i += 1

# Function to stop simulation
def stop_simulation(simulation_server_info):
    print("CLIENT: STOP SIMULATION ")
    for sim in simulation_server_info["servers"]:
        ip = sim['ip']
        port =sim['port']
        print('.... IP Add: ',ip, 'Port Number: ',port)
        # Form the base URL for the current simulation server
        base_url = f"http://{ip}:{port}"
        response = requests.get(f"{base_url}/stop_simulation")
        if response.status_code == 200:
            data = response.json()
            server_time = data.get('time', 0.0)
            print(f"CLIENT: Simulation Stopped")  # Debug log to confirm the time
            return server_time
        else:
            print(f"Error: Could not retrieve server time, status code: {response.status_code}")
            return 0.0
        
def run_simulation(simulation_server_info):
    deploy(CONTROLLER_URL, simulation_server_info)
    init_simulation(simulation_server_info)
    simulate(simulation_server_info)
    stop_simulation(simulation_server_info)

if __name__ == "__main__":

    # Base URL for simulation controller
    CONTROLLER_URL = "http://127.0.0.1:5000"

    simulation_server_info = { 
        "servers": [
            {"id": "0", "ip": "127.0.0.1", "port": "5001"},
            {"id": "1", "ip": "127.0.0.1", "port": "5002"}
        ]
    }

    run_simulation(simulation_server_info)

