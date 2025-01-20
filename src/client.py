import requests
import time
from dataclasses import asdict, dataclass



@dataclass
class Simulator:
    id: str
    ip: str
    port: str

class Client:
    controller_url = ""
    sim_servers = []
    real_time_factor = 1.0

    def __init__(self, controller_url, server_list) -> None:
        self.controller_url = controller_url
        self.sim_servers.extend(server_list)
        print("Client initialized.")

    def deploy(self):
        json_servers = {"servers": [asdict(l) for l in self.sim_servers]}
        print("[DEBUG] JSON SERVERS: ", json_servers)

        try:
            response = requests.post(f"{self.controller_url}/deploy", json=json_servers)
            if response.status_code == 200:
                print("Simulation server(s) deployed successfully")
                print("Response:", response.json())
                return 200
            else:
                print("Failed to deploy Simulation server(s)")
                print("Response code:", response.status_code)
                print("Response:", response.text)
                return 0
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to simulation server(s): {e}")
            return 0


    def init_simulation(self, real_time_factor_target, execution_step_value, steps_to_monitor):
        
        info = {'real_time_factor_target': real_time_factor_target, 
                'execution_step_value': execution_step_value,
                'steps_to_monitor': steps_to_monitor}

        #TODO the simulation speed is no controlled by the client. it should be by the simulator.
        #TODO requires update how the simulation step is advanced.

        self.real_time_factor= real_time_factor_target

        for sim in self.sim_servers:
            try:
                ip, port = sim.ip, sim.port
                base_url = f"http://{ip}:{port}"
                response = requests.post(f"{base_url}/init", json={"body": info})
                #print("CLIENT.INIT: ", response)
                
                if response.status_code == 200:
                    print(f"[INFO] Server {sim.id} initialized successfully")
                else:
                    print(f"[ERROR] Failed to initialize Server {sim.id}")
                    return 0
                
            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Exception occurred while initializing Server {sim.id}: {str(e)}")
                return 0
        return 200 #all servers initilized

    def get_waypoints_for_time(self, requested_time, events):
        matching_events = {}
        waypoint_found = False
        for event in events:
            event_time = event["time"]
            if int(requested_time) == int(event_time):
                matching_events[event["variable"]] = event["value"]
                waypoint_found = True
        return matching_events if waypoint_found else None


    def send_wp(self, sim, waypoints, current_simulation_time):
        base_url = f"http://{sim.ip}:{sim.port}"
        response = requests.post(f"{base_url}/next_wp", json={
            "waypoints": waypoints
        })
        if response.status_code == 200:
            print(f"[INFO] Waypoints sent to {sim.id} at time {current_simulation_time}")
        else:
            print(f"[ERROR] Unable to send waypoints to server {sim.id}, status code: {response.status_code}")

    def get_pos_all(self):
        return [self.get_curr_pos(s) for s in self.sim_servers]

    def get_curr_pos(self, sim_s):
        base_url = f"http://{sim_s.ip}:{sim_s.port}"
        ref_response = requests.get(f"{base_url}/current_pos")
        if ref_response.status_code == 200:
            return ref_response.json()
        else:
            print(f"[ERROR] Failed to fetch current position from {sim_s.id}")
            # should return an error message
            return {"time": 0, "x_act": 0, "y_act": 0, "psi_act": 0, "fuel": 0}

    def stop_simulation(self):
        for sim in self.sim_servers:
            base_url = f"http://{sim.ip}:{sim.port}"
            response = requests.get(f"{base_url}/stop_simulation")
            if response.status_code == 200:
                print(f"Simulation stopped on {sim.id}")
            else:
                print(f"[ERROR] Unable to stop simulation on {sim.id}")


    def advance_simulation(self, cycles, cycle_len=1):
        # advancing simulation time requires GET cur_pos of each server
        print(f"Advancing {cycles} time units ")
        pos = []
        for i in range(cycles):
            time.sleep(cycle_len/self.real_time_factor)
            pos = self.get_pos_all()
                
        # returm the current time of servers
        return [pos[i] for i in range(len(self.sim_servers))]
    
    def _flatten_sequence(self, wp_sequence):
        #flatten the sequence in format to
        # wps_flat=[
        #         {"ship": "0", "time": 50,  "x_wp"  : 20.0},
        #         {"ship": "0", "time": 50,  "x_tp"  : 250.0},
        #         {"ship": "1", "time": 60,  "x_wp"  : 20.0},
        #         {"ship": "1", "time": 60,  "x_tp"  : 250.0},
        # ]
        
        wp_sequence_flat =[]
        for s in wp_sequence:
            for entry in wp_sequence[s]:
                entry["ship"]=s
                wp_sequence_flat.append(entry)

        #print("[DEBUG] flat list: ", wp_sequence_flat)
        return wp_sequence_flat
    

    def sorted_sequence(self, wp_sequence_flat):
        " sorts all events chronologically in a flat sequence"
        l  = len(wp_sequence_flat)

        #order flat sequence by time
        for j in range(0, l-1):
            for i in range(0, l-j-1):
                #print(f'{j} {i}:')
                if wp_sequence_flat[i]["time"] > wp_sequence_flat[i+1]["time"]:
                    #swap
                    tmp = wp_sequence_flat[i]
                    wp_sequence_flat[i] = wp_sequence_flat[i+1]
                    wp_sequence_flat[i+1] = tmp
                    #[print(k, wp_sequence_flat[k]) for k in range(l)]

        #print("[DEBUG] sorted list: ")
        #[print(k, wp_sequence_flat[k]) for k in range(l)]
        return wp_sequence_flat


    def simulate_sequence(self, wp_sequence):
        """
        Receive a sequence of WPs for all servers and returns the actual positions
        """
        act_pos = []

        wp_sequence_flat = self._flatten_sequence(wp_sequence)

        wp_sequence_sorted = self.sorted_sequence(wp_sequence_flat)

                

        # get current simulation time, we assume both servers have same time, so one is enough
        crt_time = self.advance_simulation(1)[0]["time"]

        crt_index =0 # which entry is processed

        while crt_index < len(wp_sequence_sorted)-1:
            wp_time = wp_sequence_sorted[crt_index]["time"]
            print(f"crt_time: {crt_time} wp_time: {wp_time}")

            if crt_time < wp_time:
                crt_pos = self.advance_simulation(1)
                crt_time = crt_pos[0]["time"]
                act_pos.append(crt_pos)

            #elif wp_time==crt_time:
            else: #do we need to add a tolerance?
                #print(f"sending {wp_sequence_sorted[crt_index]} at time {crt_time}")
                # TODO ugly processing. To be optimized
                server_instance= self.sim_servers[int(wp_sequence_sorted[crt_index]["ship"])]
                variable_str = list(wp_sequence_sorted[crt_index].keys())[1] # we know it is hardcoded above on position 1
                variable_val = wp_sequence_sorted[crt_index][variable_str]

                #print(f"Sending WP: server_id {server_instance.id} variable_str {variable_str} variable_val {variable_val}")

                #TODO store and append actual pos
                #sending WP      
                self.send_wp(server_instance, 
                     [{"time": wp_time, 
                        variable_str : variable_val
                     }], crt_time)
                
                #moving to next wp in list
                crt_index+=1
            #else:
            #    print("ERROR: simulation time is behind wp time")
            
        print("[Info] Sequence completed ")
        return act_pos   
              




