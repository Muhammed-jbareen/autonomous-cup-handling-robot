import xarm
from time import sleep
import configparser

arm = xarm.Controller('USB')

config = configparser.ConfigParser()

config.read('config.ini')

GRIP_SERVO_ID = int(config.get('Arm', 'GRIP_ID'))
GRIP_ROTATION_SERVO_ID = int(config.get('Arm', 'GRIP_ROTATION_ID'))
TOP_SERVO_ID = int(config.get('Arm', 'TOP_ID'))
MIDDLE_SERVO_ID = int(config.get('Arm', 'MIDDLE_ID'))
BASE_SERVO_ID = int(config.get('Arm', 'BASE_ID'))
BASE_ROTATION_SERVO_ID = int(config.get('Arm', 'BASE_ROTATION_ID'))

# The coefficient is basically how much millieseconds we want to wait for each unit we move, for a movement of total 100 units for example, we would need to wait 100 * coefficient_of_units_delta millieseconds.
coefficient_of_units_delta = float(config.get('General', 'coefficient_of_units_delta'))

GRIP_SERVO = xarm.Servo(GRIP_SERVO_ID)
GRIP_ROTATION_SERVO = xarm.Servo(GRIP_ROTATION_SERVO_ID)
TOP_SERVO = xarm.Servo(TOP_SERVO_ID)
MIDDLE_SERVO = xarm.Servo(MIDDLE_SERVO_ID)
BASE_SERVO = xarm.Servo(BASE_SERVO_ID)
BASE_ROTATION_SERVO = xarm.Servo(BASE_ROTATION_SERVO_ID)


"""
grip servo: from 150 - 600 (median 400 but set to 600), deviation = 0
grip rotation servo: from 0 - 1000 (median 500), deviation = 0
top servo: from 45 - 1000 (median at 500)
middle servo: from 0 - 1000 (median at 500 but start from 230)deviation = 0
base servo: range from 125 - 480 (median at 205 but start from 150) deviation = -100
base rotation servo: range from 0 - 510 (median at 205) deviation = 0

just joking, apparently I didn't build the arm correctly the first time, I had to disintegrate lots of the arm and adjust the servos and then build it again.

grip servo: range from 150 - 680 (start at 680) closes completly at 680.
grip rotation servo: range from 0 - 1000, start at 500.
top servo: range from 0 - 1000, start at 500.
middle servo: range from 0 - 1000, start at 500.
base servo:  range from 0 - 1000, start at 500
base rotation servo: range from 0 - 1000, start at 500
"""
def getServoPos(servoId):
	return arm.getPosition(servoId)
def move_servo(servo_id, start, end, coefficient_of_units_delta, wait = False):
	
	# start and end needs to be in units and not in degrees, if in degrees then the coefficient needs to be multiplied by 4 to yield the same movement time( (-)125-125 degrees -> 250 degrees, 0-1000 units -> 1000/250 = 4)
	# coefficient_of_degrees_delta would be 20 (4 * 5) in this case
	movement_time = int(abs(start - end) * coefficient_of_units_delta)
	
	arm.setPosition(servo_id, end, duration = movement_time, wait = wait)

"""
Moves the base, middle, grip, and top servos in sync,
auto-adjusting top_servo to maintain x-axis alignment.
"""
def move_arm_with_stabilizing(base_servo_end_position, middle_servo_end_position, grip_servo_end_position, wait_for_top_servo = False, wait_for_grip_servo = False):
	# This function's goal is to align the top servo with the x-axis.
		
	base_servo_start_position = arm.getPosition(BASE_SERVO_ID)
	grip_servo_start_position = arm.getPosition(GRIP_SERVO_ID)
	middle_servo_start_position = arm.getPosition(MIDDLE_SERVO_ID)		
	top_servo_start_position = arm.getPosition(TOP_SERVO_ID)
		
	""" Calculating the position of the top servo """
	
	# A complete explaination of the calculation of the equation below is provided in another file.
	if base_servo_end_position == -1:
		top_servo_end_position = 850 - (middle_servo_end_position - 500) - (base_servo_start_position - 500)	
	else:
		# A complete explaination of the calculation of the equation below is provided in another file.
		top_servo_end_position = 850 - (middle_servo_end_position - 500) - (base_servo_end_position - 500)	
	
	largest_servo_movement = max(abs( base_servo_start_position - base_servo_end_position), abs(middle_servo_start_position - middle_servo_end_position), abs(top_servo_start_position - top_servo_end_position), abs(grip_servo_start_position - grip_servo_end_position))
	if grip_servo_end_position != -1:
		move_servo(GRIP_SERVO_ID, grip_servo_start_position, grip_servo_end_position, coefficient_of_units_delta, wait = wait_for_grip_servo)
		
	sleep(0.05)
	
	move_servo(TOP_SERVO_ID, top_servo_start_position, top_servo_end_position, coefficient_of_units_delta)
	
	if wait_for_top_servo:
		sleep(0.45)
	else:
		sleep(0.05)
	
	if base_servo_end_position != -1:
		move_servo(BASE_SERVO_ID, base_servo_start_position, base_servo_end_position, coefficient_of_units_delta)
		sleep(0.05)
	if middle_servo_end_position != -1:
		move_servo(MIDDLE_SERVO_ID, middle_servo_start_position, middle_servo_end_position, coefficient_of_units_delta)
		
	return largest_servo_movement
	
"""
 * cup_relative_distance: cup_relative_distance is a parameter that represents the number of pixels that the cup occupies divided by the number of the pixels in the picture, 
 the range of this parameter is (0, 1)
 * cup_height: cup_height is a parameter that represents the height of the cup in pixels divided by the height of the picture, the range of this parameter is (0, 1)
 * cup_width: cup_width is a parameter that represents the width of the cup in pixels divided by the width of the picture, the range of this parameter is (0, 1)
"""
def reach_for_cup(cup_relative_distance, cup_height, cup_width):
	base_servo_rotation_end_pos = 500
	base_servo_end_position = 850
	# the 350 that is multiplied by cup_relative_distance is a hyperparameter that we can tamper with, the 850 is the position where the middle servo is on the x axis(so 350 * cup_relative_distance is an offset from the x-axis, it determines how much we want the middle servo to stretch)
	#middle_servo_end_position = int(850 - 350 * cup_relative_distance)
	middle_servo_end_position = 830
	grip_servo_end_position = 150
	grip_servo_rotation_end_position = 500
	
	move_servo(BASE_ROTATION_SERVO_ID, arm.getPosition(BASE_ROTATION_SERVO_ID), base_servo_rotation_end_pos, coefficient_of_units_delta, wait = True)
	
	move_servo(GRIP_ROTATION_SERVO_ID, arm.getPosition(GRIP_ROTATION_SERVO_ID), grip_servo_rotation_end_position, coefficient_of_units_delta)
	
	sleep(0.05)
	
	largest_servo_movement = move_arm_with_stabilizing(base_servo_end_position, middle_servo_end_position, grip_servo_end_position, wait_for_grip_servo = True)
	
	sleep( (largest_servo_movement * coefficient_of_units_delta) / 1000)
	

def grab_cup():
	base_servo_end_position = 600
	middle_servo_end_position = 650
	grip_servo_end_position = 550
	
	largest_servo_movement = move_arm_with_stabilizing(base_servo_end_position, middle_servo_end_position, grip_servo_end_position, wait_for_grip_servo = True)
	
	sleep( (largest_servo_movement * coefficient_of_units_delta) / 1000)
	
def pour_cup():
	middle_servo_end_position = 630
	base_rotation_servo_end_position = 510
	grip_rotation_servo_end_position = 950
	base_servo_end_position = 730
	
	move_servo(BASE_ROTATION_SERVO_ID, arm.getPosition(BASE_ROTATION_SERVO_ID), base_rotation_servo_end_position, coefficient_of_units_delta, wait = True)
	
	largest_servo_movement = move_arm_with_stabilizing(base_servo_end_position, middle_servo_end_position, -1)
	
	sleep( (largest_servo_movement * coefficient_of_units_delta) / 1000)
	
	move_servo(GRIP_ROTATION_SERVO_ID, arm.getPosition(GRIP_ROTATION_SERVO_ID), grip_rotation_servo_end_position, coefficient_of_units_delta)

	
def put_cup():
	base_servo_end_position = 825
	base_servo_rotation_end_position = 500
	middle_servo_end_position = 850
	grip_servo_end_position = 150
	grip_servo_rotation_end_position = 500
	
	move_servo(GRIP_ROTATION_SERVO_ID, arm.getPosition(GRIP_ROTATION_SERVO_ID), grip_servo_rotation_end_position, coefficient_of_units_delta)
	sleep(0.5)
	move_servo(BASE_ROTATION_SERVO_ID, arm.getPosition(BASE_ROTATION_SERVO_ID), base_servo_rotation_end_position, coefficient_of_units_delta)
	sleep(0.1)
	
	largest_servo_movement = move_arm_with_stabilizing(base_servo_end_position, middle_servo_end_position, -1, wait_for_top_servo = True)
	
	sleep( (largest_servo_movement * coefficient_of_units_delta) / 1000)
	
	move_servo(GRIP_SERVO_ID, arm.getPosition(GRIP_SERVO_ID), grip_servo_end_position, coefficient_of_units_delta, wait = True)
	
def initial_pos(wait = False):
	arm.setPosition(BASE_SERVO_ID, 500, 1000, True)
	arm.setPosition(GRIP_SERVO_ID, 680, 1000) 
	arm.setPosition(GRIP_ROTATION_SERVO_ID, 500, 1000)  
	arm.setPosition(TOP_SERVO_ID, 500, 1000)
	arm.setPosition(MIDDLE_SERVO_ID, 500, 1000)
	arm.setPosition(BASE_ROTATION_SERVO_ID, 500, 1000)
	
	if wait == True:
		sleep(4)

def turn_off_servos():
	arm.servoOff([GRIP_SERVO, GRIP_ROTATION_SERVO, TOP_SERVO, MIDDLE_SERVO, BASE_SERVO, BASE_ROTATION_SERVO])
