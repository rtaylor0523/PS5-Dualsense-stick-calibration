# PS5-Dualsense-Stick-Calibration
Stick drift is a controller malfunction in which either controller stick can perform a function without user input. This malfunction causes a disruption in gameplay and the overall performance of the gamer using the controller. Stick drift can be a result of either issues in hardware or software. In this project, I created a GUI to recalibrate a PS5 Dualsense controller and elimated any software bugs in the controller's code. 

**Add Ons**

The script I used was adapted from [https://github.com/ditls/ds4-tools)](https://github.com/dualshock-tools/ds4-tools) and I added a live view of controller stick movement when the controller is connected to the whatever device the GUI is presented on. This allows the user to visualize how the sticks' movement with or without their imput, as well as showcase the results of the calibration process where the stick remains at rest in the center of the x-y plane. 

The GUI also presents users with the option to alter the size of their deadzone. The deadzone is the space in which the user input is not registered by the the controller sticks. This option comes in the form of a slider, where the default setting is 5. Users can choose to increase or decrease the size of the deadzone radius using this slider (More competitive gamers may decrease the size of their deadzone to allow the sticks to be more sensitve to user input). The altered deadzone size is visualized on the same x-y plane used to demonstrate realtime stick movement. 

Another addition to the script was the abiltity to make the calibration results permanent to the script. This is shown in the GUI as a checkbox with "Make changes permanent next" to it.


**How to Use**


