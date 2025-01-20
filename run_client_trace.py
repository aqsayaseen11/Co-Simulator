from src.client import  Client, Simulator


if __name__ == "__main__":

    # #TODO we can start the controller here

    # ### Define configuration and simulation parameters
    
    # #list of simmulators (ships)
    s1 = Simulator("0", "127.0.0.1", "5001")
    s2 = Simulator("1", "127.0.0.1", "5002")
    C_URL ="http://127.0.0.1:5000" #TODO make it a class

    ### Initialize and deploy
    client = Client(controller_url=C_URL, server_list=[s1, s2])
    assert client.deploy(), "Deployment failed"

    assert client.init_simulation(
        real_time_factor_target=20,
        execution_step_value=25,
        steps_to_monitor=5), "init failed"
    
    
    #an example planned trajectory
    collision_trace = {
        "0" : [
                {"time": 50, "x_wp"  : 500.0},
                {"time": 50, "x_tp" : 7500.0},
                {"time": 6500, "psi_wp"  : 1.5},
                {"time": 6500, "psi_tp" : 7350.0},
                {"time": 7000, "y_wp"  : 700.0},
                {"time": 7000, "y_tp" : 15000.0},
                {"time": 15000, "y_wp"  : 900.0},
                {"time": 15000, "y_tp" : 15000.0},

            ], 
        "1" : [
                {"time": 50, "y_wp"  : 500.0},
                {"time": 50, "y_tp" : 7500.0},
                {"time": 6500, "psi_wp"  : 0.0},
                {"time": 6500, "psi_tp" : 7350.0},
                {"time": 7000, "x_wp"  : 700.0},
                {"time": 7000, "x_tp" : 15000.0},
                {"time": 15000, "x_wp"  : 900.0},
                {"time": 15000, "x_tp" : 15000.0},

            ]}

    colreg_trace = {
        "0" : [ 
                {"time": 50, "x_wp"  : 500.0},
                {"time": 50, "x_tp" : 7500.0},
                {"time": 6500, "psi_wp"  : 1.5},
                {"time": 6500, "psi_tp" : 7350.0},
                {"time": 7000, "y_wp"  : 700.0},
                {"time": 7000, "y_tp" : 15000.0},
                {"time": 15000, "y_wp"  : 900.0},
                {"time": 15000, "y_tp" : 15000.0},

            ], 
        "1" : [
                {"time": 50, "y_wp"  : 500.0},
                {"time": 50, "y_tp" : 7500.0},
                {"time": 6500, "psi_wp"  : 0.0},
                {"time": 6500, "psi_tp" : 7350.0},
                {"time": 7000, "x_wp"  : 700.0},
                {"time": 7000, "x_tp" : 13000.0},
                {"time": 10000, "psi_wp"  : -1.5},
                {"time": 10000, "psi_tp" : 12350.0},
                {"time": 10000, "y_wp"  : 400.0},
                {"time": 10000, "y_tp" : 12000.0},
                {"time": 12000, "x_wp"  : 900.0},
                {"time": 12000, "x_tp" : 15000.0},
                {"time": 15000, "x_wp"  : 1000.0},
                {"time": 15000, "x_tp" : 16000.0},
            ]}

    no_colreg_trace = {
        "0" : [ 
                {"time": 50, "x_wp"  : 500.0},
                {"time": 50, "x_tp" : 7500.0},
                {"time": 6500, "psi_wp"  : 1.5},
                {"time": 6500, "psi_tp" : 7350.0},
                {"time": 7000, "y_wp"  : 700.0},
                {"time": 7000, "y_tp" : 15000.0},
                {"time": 15000, "y_wp"  : 900.0},
                {"time": 15000, "y_tp" : 15000.0},

            ], 
        "1" : [
                {"time": 50, "y_wp"  : 500.0},
                {"time": 50, "y_tp" : 7500.0},
                {"time": 6500, "psi_wp"  : 0.0},
                {"time": 6500, "psi_tp" : 7350.0},
                {"time": 7000, "x_wp"  : 700.0},
                {"time": 7000, "x_tp" : 13000.0},
                {"time": 11200, "psi_wp"  : -1.5},
                {"time": 11200, "psi_tp" : 12350.0},
                {"time": 11350, "y_wp"  : 400.0},
                {"time": 11350, "y_tp" : 12000.0},
                {"time": 12400, "x_wp"  : 900.0},
                {"time": 12400, "x_tp" : 15000.0},
                {"time": 15000, "x_wp"  : 1000.0},
                {"time": 15000, "x_tp" : 16000.0},
            ]}
    #offline execution
    actual_trace = client.simulate_sequence(no_colreg_trace)
    #print("[Info] Resulting actual trace: ",  " ".join([str(x) for x in actual_trace]))

    client.advance_simulation(10000)
    # ### Ending simulation
    client.stop_simulation()
    print("Client stopped.")
