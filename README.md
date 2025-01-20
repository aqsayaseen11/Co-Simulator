# ColregSimulator
The platform is developed using Python and is based on the client-server architecture for providing real-time interactions, data transfer, and graphical representation.
It has three simulation scenarios where the reference waypoints for navigation routes are generated for two vessels whose planned navigational path encounters a risk of collision in a crossing situation.
Scenario 1: Risk of collision in a crossing situation (in the absence of waypoints provided by a trajectory planning tool)
Scenario 2: Attempted collision avoidance in a crossing situation (as per Rule 15 and Rule 16)
Scenario 3: Collision avoidance in a crossing situation as per COLREG Rule 15 and Rule 16
For better understanding check my Master's thesis Co-Simulator: A Platform for Integrating Trajectory Planning Tools and Co-Simulation Environments available online 
https://urn.fi/URN:NBN:fi-fe202501164094


Instructions on running:
1. Start Simulation Controller 
	python src/controller.py
2. Open the browser and navigate to the IP:PORT(default http://127.0.0.1:5000) of the Simulation Controller
3. Start the instantiate and run a client 
    python run_client_trace.py
	
