from flask import Flask, jsonify, request, render_template
from libcosimpy.CosimExecution import CosimExecution
from libcosimpy.CosimObserver import CosimObserver
from libcosimpy.CosimManipulator import CosimManipulator
import os
import csv
import argparse
import time
from datetime import datetime
import sys
 
#TODO make this a class https://stackoverflow.com/questions/40460846/using-flask-inside-class

#TODO simulator should return error code when something fails, and the process should exit/be killed

#TODO controller should be aware when the simulators exit

import logging
#disable request logging in console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# Global variables 
execution = None
observer = None
time_series_observer = None  
manipulator = None
logical_simulation_time = 0.0  

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Run the Flask app with simulation parameters.")
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host IP address for the Flask server')
parser.add_argument('--port', type=int, default=5000, help='Port for the Flask server')
parser.add_argument('--sid', type=str, default="0", help='Simulation server ID')
args = parser.parse_args()

# Assign the parsed arguments to variables
simulation_time_step = 1  # Time step in seconds
steps_to_monitor = 5  # Steps to monitor #TODO add as init parameter

previous_waypoints = {
    'x_wp': None,
    'y_wp': None,
    'psi_wp': None,
    'x_tp': None,
    'y_tp': None,
    'psi_tp': None
}

# signal mappings
variables_id = {
    'x_wp': 31,     #x_waypoint
    'y_wp': 33,     #y_waypoint
    'psi_wp': 29,   #psi_waypoint
    'x_tp': 30,     #simulation time when x_tp should be reached
    'y_tp': 32,     #simulation time when y_tp should be reached
    'psi_tp': 28,   #simulation time when psi_tp should be reached
    'x_ref': 38,    #x_reference value
    'y_ref': 39,    #y_reference value
    'psi_ref': 37,  #psi_reference value
    'x_act': 49,    #x_actual value
    'y_act': 51,    #y_actual value
    'psi_act': 44   #psi_actual value
}

# module mappings
slave_index_id = {
    'reference_generator': 4,
    'dp_controller': 2
}

# TODO replace with server status when becomes available
start_plot=False
current_datetime = " "


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/init', methods=['POST'])
def init():
    global execution, observer, time_series_observer
    global manipulator, simulation_running
    global logical_simulation_time, current_datetime
    global execution_step_value

    try:
        # Get payload from the request
        data = request.get_json()
        payload = data.get('body', {})
        print(f"[DEBUG] Initializing Server {args.sid} at {args.host}:{args.port}")
        print(f"[DEBUG] Payload Received for Server {args.sid}: {payload}")

        #### Extract Initialization Values
        real_time_factor_target = payload.get('real_time_factor_target')
        steps_to_monitor = payload.get('steps_to_monitor')
        execution_step_value = payload.get('execution_step_value')

        assert real_time_factor_target, f"[ERROR] real_time_factor_target is None. Stopping ..."
        
        assert steps_to_monitor, f"[ERROR] steps_to_monitor is None. Stopping ..."
            
        assert execution_step_value, f"[ERROR] execution_step_value is None. Stopping ..."

        #TODO handle assertionError and inform controller

        print(f"[DEBUG][Server {args.sid}] Real-time Factor: {real_time_factor_target}, execution_step_value {execution_step_value}")

        #### Resolve Paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dp_ship_folder = os.path.join(base_dir, 'dp-ship')
        print(f"[DEBUG][Server {args.sid}] Resolved OSP Config Path: {dp_ship_folder}")

        #### Initialize CosimExecution
        execution = CosimExecution.from_osp_config_file(osp_path=dp_ship_folder)
        if not execution:
            print(f"[ERROR][Server {args.sid}] Failed to initialize CosimExecution.")
            return jsonify({"error": "Failed to initialize CosimExecution"}), 500
        print(f"[DEBUG][Server {args.sid}] CosimExecution initialized successfully.")

        #### Initialize Observers and Manipulators
        
        observer = CosimObserver.create_last_value()
        time_series_observer = CosimObserver.create_time_series()
        manipulator = CosimManipulator.create_override()
        print(f"[DEBUG][Server {args.sid}] Observers and Manipulator Created.")

        # Add Observers and Manipulator
        if execution.add_observer(observer=observer) and execution.add_observer(observer=time_series_observer):
            print(f"[DEBUG][Server {args.sid}] Observers added successfully.")
        else:
            print(f"[ERROR][Server {args.sid}] Failed to add observers.")

        if execution.add_manipulator(manipulator=manipulator):
            print(f"[DEBUG][Server {args.sid}] Manipulator added successfully.")
        else:
            print(f"[ERROR][Server {args.sid}] Failed to add manipulator.")

        #### Enable Real-time Simulation
        if execution.real_time_simulation_enabled(True):
            print(f"[DEBUG][Server {args.sid}] Real-time simulation enabled.")
        else:
            print(f"[ERROR][Server {args.sid}] Failed to enable real-time simulation.")

        # Set Real-time Factor and Steps to Monitor
        if execution.real_time_factor_target(real_time_factor_target):
            print(f"[DEBUG][Server {args.sid}] Real-time factor set to {real_time_factor_target}.")
        else:
            print(f"[ERROR][Server {args.sid}] Failed to set real-time factor.")

        if execution.steps_to_monitor(steps_to_monitor):
            print(f"[DEBUG][Server {args.sid}] Steps to monitor set to {steps_to_monitor}.")
        else:
            print(f"[ERROR][Server {args.sid}] Failed to set steps to monitor.")

        #### Set Initial Values
        simulation_running = True
        logical_simulation_time = 0.0
        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        #### Return Initial State
        act_position = observer.last_real_values(
            slave_index=slave_index_id['dp_controller'], 
            variable_references=[
                variables_id['x_act'],
                variables_id['y_act'],
                variables_id['psi_act']
            ])
        x_act, y_act, psi_act = act_position
        nano_time = execution.status().current_time  # Get simulation time
        t = float(nano_time) * 1e-9  # Convert nanoseconds to seconds
        response_data = {'time': t, 'x_act': x_act, 'y_act': y_act, 'psi_act': psi_act}

        print(f"[DEBUG][Server {args.sid}] Initialization completed successfully with response data: {response_data}")
        return jsonify({"status": "success", "data": response_data})

    except Exception as e:
        print(f"[ERROR][Server {args.sid}] Exception in /init: {str(e)}")
        sys.exit(f"[ERROR][Server {args.sid}] Exception in /init: {str(e)}")
        #return jsonify({"error": "Exception during initialization", "details": str(e)}), 500


@app.route('/next_wp', methods=['POST'])
def next_wp():
    global previous_waypoints, logical_simulation_time
    global simulation_time_step, start_plot, execution
    #global variables_id

    if execution:
        # Fetch the current time sent by the client
        data = request.get_json()

        # Get the waypoints from the client (if provided) and update the simulation state
        waypoints = data['waypoints']
        print(f"[Server {args.sid}] RECEIVED WAYPOINTS", waypoints)

        # Update the previous waypoints with new values
        # print(f"[DEBUG] Previous Waypoints Before Update: {previous_waypoints}")
        for wp in waypoints:
            variable = list(wp.keys())[1]
            value = wp[variable]
            #print(f"[Server {args.sid}]", variable, value)
            if variable in previous_waypoints:
                previous_waypoints[variable] = value
        # Replace None values with 0.0 for missing keys

        for key in previous_waypoints:
            if previous_waypoints[key] is None:
                previous_waypoints[key] = 0.0
        
        #print(f"[DEBUG] Previous Waypoints After Update: {previous_waypoints}")

        # Apply the waypoints to the simulation
        variable_references = [
            variables_id['x_wp'],
            variables_id['y_wp'],
            variables_id['psi_wp'],
            variables_id['x_tp'],
            variables_id['y_tp'],
            variables_id['psi_tp']
        ]  
        values = [
            previous_waypoints['x_wp'],
            previous_waypoints['y_wp'],
            previous_waypoints['psi_wp'],
            previous_waypoints['x_tp'],
            previous_waypoints['y_tp'],
            previous_waypoints['psi_tp']
        ]
        
        slave_index = slave_index_id['reference_generator']  
        success = manipulator.slave_real_values(slave_index, variable_references, values)

        if success:
            start_plot=True
            #print(f"[Info][Server {args.sid}] Waypoints applied successfully at time {logical_simulation_time}")
            return jsonify({"message": "Waypoints applied successfully", "waypoints": previous_waypoints})
        else:
            print(f"[ERROR][Server {args.sid}]Failed to apply waypoints", flush=True)
            return jsonify({"error": "Failed to apply waypoints"}), 500
    else:
        # print(f"[ERROR][Server {args.sid}] not initialized", flush=True)
        return jsonify({"error": f"[ERROR][Server {args.sid}] not initialized"}), 500


@app.route('/current_pos', methods=['GET'])
def current_position():
    global observer, time_series_observer, logical_simulation_time
    global execution, slave_index_id, execution_step_value

    if execution:

        # Increment the logical simulation time step-wise
        logical_simulation_time += simulation_time_step

        execution.step(execution_step_value) # Currently, simulation is paused  but Simulation runs 25 steps (1 second) once it is executed.
        act_position = observer.last_real_values(
                slave_index= slave_index_id['dp_controller'], 
                variable_references=[        
                        variables_id['x_act'],
                        variables_id['y_act'],
                        variables_id['psi_act']
        ])
        x_position, y_position, psi_position = act_position

        nano_time = execution.status().current_time  # Assuming this is an integer in nanoseconds
        time = float(nano_time) * 1e-9  # Convert nanoseconds to seconds
        time = round(time, 1)
        
        ref_values = {
            "time": time,  # Return the logical simulation time
            "x_act": x_position,
            "y_act": y_position,
            "psi_act": psi_position,
            "start_plot":start_plot,
            'fuel': 0
        
        }
        #print('SSID: ',{'ip':args.host,'port':args.port})
        #print(ref_values)
        
        print(f"[Server {args.sid}] SIM TIME: ", ref_values["time"])
        #logging.debug("SYS TIME", datetime.now())
        return jsonify(ref_values)
    else: 
        # print(f"[ERROR][Server {args.sid}] not initialized", flush=True)
        return jsonify({"error": f"[ERROR][Server {args.sid}] not initialized"}), 500
    

@app.route('/get_data', methods=['GET'])
def get_data():
    '''
    provides data to the controller for plotting.
    TODO: can it be combined with /curr_pos?
    '''

    global observer, time_series_observer
    global logical_simulation_time, execution, current_datetime
    global slave_index_id, execution_step_value
    
    if execution:
        # Get reference and actual values for plotting
        ref_gen_position = observer.last_real_values(
                #slave_index=slave_index_id['reference_generator'], 
                slave_index=slave_index_id['reference_generator'], 
                variable_references=[
                    variables_id['x_ref'],
                    variables_id['y_ref'],
                    variables_id['psi_ref']])
        x_ref_position, y_ref_position, psi_ref_position = ref_gen_position
        #print(f"[DEBUG] Server {args.sid} ref_gen_position", ref_gen_position)

        act_position = observer.last_real_values(
            slave_index=slave_index_id['dp_controller'], 
            variable_references=[        
                variables_id['x_act'],
                variables_id['y_act'],
                variables_id['psi_act']])
        x_position, y_position, psi_position = act_position
        #print(f"[DEBUG] Server {args.sid} act_position", act_position)

        # Add the waypoint values from the previous waypoints
        x_wp = previous_waypoints.get('x_wp', 0)
        y_wp = previous_waypoints.get('y_wp', 0)
        psi_wp = previous_waypoints.get('psi_wp', 0)

        x_tp = previous_waypoints.get('x_tp', 0)
        y_tp = previous_waypoints.get('y_tp', 0)
        psi_tp = previous_waypoints.get('psi_tp', 0)
    
        nano_time = execution.status().current_time  # Assuming this is an integer in nanoseconds
        time = float(nano_time) * 1e-9  # Convert nanoseconds to seconds


        ref_values = {
            'ssid':{'ip':args.host,'port':args.port},
            "time": time,  # Return the logical simulation time
            "x_ref": x_ref_position,
            "y_ref": y_ref_position,
            "psi_ref": psi_ref_position,
            "x_act": x_position,
            "y_act": y_position,
            "psi_act": psi_position,
            "x_wp": x_wp,
            "y_wp": y_wp,
            "psi_wp": psi_wp,
            "start_plot":start_plot,
            "x_tp": x_tp,  
            "y_tp": y_tp,  
            "psi_tp": psi_tp,  
        }

        log_folder = "src/log"
        # Generate CSV file path for each SSID based on IP, port, date, and time
        csv_file = os.path.join(log_folder, f"{ref_values['ssid']['ip']}_{ref_values['ssid']['port']}_{current_datetime}.csv")
    
        # Check if the file already exists
        file_exists = os.path.isfile(csv_file)

        #TODO move this to controller to be done in a centralized manner
        # Append data to the appropriate CSV file
        with open(csv_file, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=ref_values.keys())

            # If the file does not exist, write the header first
            if not file_exists:
                writer.writeheader()

            # Write the data row
            writer.writerow(ref_values)

        return jsonify(ref_values)
    else:
        #print(f"[ERROR][Server {args.sid}] not initialized", flush=True)
        return jsonify({"error": f"[ERROR][Server {args.sid}] not initialized"}), 500
    

@app.route('/stop_simulation', methods=['GET'])
def stop_simulation():
    #print(f"[Server {args.sid}]: STOPPING SIMULATION")

    global execution, simulation_running

    if execution:
        execution.stop()  # Ensure this stops the simulation gracefully
        simulation_running = False
        print(f"[Server {args.sid}]: Simulation stopped.", flush=True)
        return jsonify({"message": f"[Server {args.sid}] Simulation stopped"})
    else:
        return jsonify({"error": f"[Server {args.sid}] Simulation not running"}), 400


@app.route('/health', methods=['GET'])
def health_check():
    if execution:
        return jsonify({'status': 'running'}), 200
    else:
        return jsonify({'status': 'not running'}), 500

if __name__ == "__main__":
    time.sleep(5)
    print("Sim server ID: ", args.sid)
    app.run( host=args.host, port=args.port)
