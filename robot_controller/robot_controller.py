import xarm
from time import sleep
import configparser
from arm_controller import reach_for_cup, grab_cup, pour_cup, put_cup, initial_pos
from multiprocessing.shared_memory import SharedMemory
import struct
import smbus
import sys
import math
from shared_protocol import *

config = configparser.ConfigParser()

config.read('config.ini')

vcc = float(config.get('General', 'vcc_voltage'))
shared_memory_name = str(config.get('General', 'shared_memory_name'))

shared_mem = SharedMemory(name=shared_memory_name)

image_size = int(config.get('Camera', 'image_size')) # Height = width
camera_fov = float(config.get('Camera', 'camera_fov'))

if image_size > 320:
    image_size = 320

# I2C bus number, usually 1, but I accidantely fried my raspberry pi's bus number 1 by supplying a 5v signal to its GPIO pins
I2C_BUS = 3

# Set the I2C address of the 4-ch encoder motor driver
MOTOR_ADDR = 0x34 

#Register address
ADC_BAT_ADDR = 0x00
MOTOR_TYPE_ADDR = 20 
MOTOR_ENCODER_POLARITY_ADDR = 21 
MOTOR_FIXED_SPEED_ADDR = 51 

MOTOR_TYPE_JGB37_520_12V_110RPM = 3 

#Motor type and encoder direction polarity
MotorType = MOTOR_TYPE_JGB37_520_12V_110RPM
MotorEncoderPolarity = 0

bus = smbus.SMBus(I2C_BUS)

GRAB_SIZE_WHITE = 0.13
GRAB_SIZE_RED = 0.16

ACTUAL_MAX_SPEED = 50
EFFECTIVE_MAX_SPEED = 40 # max speed is actually 50, but 50 is way too fast, so for that matter, we set it to 40.
MIN_SPEED = 0
DEFAULT_SPEED = 10

move_forward_polarity = [1, -1, -1, 1]
move_backward_polarity = [-1, 1, 1, -1]
rotate_right = [-DEFAULT_SPEED, DEFAULT_SPEED, -DEFAULT_SPEED, DEFAULT_SPEED]
rotate_left = [DEFAULT_SPEED, -DEFAULT_SPEED, DEFAULT_SPEED, -DEFAULT_SPEED]
stop = [0, 0, 0, 0]

rotate_look_right = [-DEFAULT_SPEED, DEFAULT_SPEED, -DEFAULT_SPEED, DEFAULT_SPEED]
rotate_look_left = [DEFAULT_SPEED, -DEFAULT_SPEED, DEFAULT_SPEED, -DEFAULT_SPEED]

x_center_of_cup_previous = -1

cup_not_detected_counter = 0

def initial_motor(): #initialize motor
    bus.write_byte_data(MOTOR_ADDR, MOTOR_TYPE_ADDR, MotorType) 
    sleep(0.5)
    bus.write_byte_data(MOTOR_ADDR, MOTOR_ENCODER_POLARITY_ADDR, MotorEncoderPolarity) 

initial_pos()
initial_motor()

def request_report(size):
    if size > 255 and size < 0:
        return
    shared_mem.buf[REQUESTED_REPORTS_NUMBER_INDEX] = size
    shared_mem.buf[REQUEST_SIGNAL_INDEX] = 1
    while True:
        if shared_mem.buf[COMPLETION_SIGNAL_INDEX] == 1:
            shared_mem.buf[COMPLETION_SIGNAL_INDEX] = 0
            return

def look_for_cup(direction = 'right'):
    if direction == 'left':
        bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,rotate_look_left)
    else:
        bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,rotate_look_right)

def stop_robot():
    bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,stop)


def move_robot(direction, movement_time = -1, speed = 15):
    """
    Move the robot in a specified direction for a certain duration.

    Parameters:
    - direction (str): 'forward' or 'backward'
    - movement_time (float): time in seconds to move. If negative, moves indefinitely.
    - speed (int): motor speed from 0 to 50
    """
    if speed > 50 or speed < 0:
        speed = 15

    speeds = []

    if direction == 'forward':
        speeds = [polarity * speed for polarity in move_forward_polarity]
    else:
        speeds = [polarity * speed for polarity in move_backward_polarity]
    print(speeds)
    bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR, speeds)

    if movement_time >= 0:
        sleep(movement_time)
        bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR, stop)

# Function to convert degrees to radians
def degrees_to_radians(degrees):
    return degrees * math.pi / 180

# Function to convert radians to degrees
def radians_to_degrees(radians):
    return radians * 180 / math.pi


def calculate_battery_level():
    """" Calculating Battery Level """
    battery = bus.read_i2c_block_data(MOTOR_ADDR, ADC_BAT_ADDR)
    battery_level = battery[0] + (battery[1] << 8)
    if battery_level > 1000:
        battery_level /= 1000
    else:
        battery_level /= 100
    return battery_level

def calculate_pixel_rotation_delay():
    
    battery_level = calculate_battery_level()
    
    battery_level_normalized = ((vcc - battery_level) / vcc) * (10 ** -3) # Normalizing battery level values in range 0-0.001
    
    # image_size = 256 and camera_fov = 56.4 is the default configurations and I already calculated the pixel rotation delay for it, no need to waste time calculating it.
    if image_size == 256 and camera_fov == 57.4:
        pixel_rotation_delay = 0.0128141015625
        return pixel_rotation_delay + battery_level_normalized
    
    # All of the calculations below are explained in details in the presentation
                                          
    #beta represents the angle we need to rotate so we displace exactly by one pixel.
    beta = camera_fov / image_size
        
    # this is a macnum wheel, so the calculations are a bit different.
    wheel_radius = 4.85
    wheel_half_circumference = (2 * math.pi * wheel_radius) / 2
    
    chasis_width = 25.6
    chasis_length = 29.7
    
    diameter_of_chasis_rotation_circle = math.sqrt( chasis_width ** 2 + chasis_length ** 2 )
    chasis_rotation_circle_radius = diameter_of_chasis_rotation_circle / 2
    
    chasis_rotation_circle_circumference = 2 * math.pi * chasis_rotation_circle_radius
    
    degrees_rotated_in_full_wheel_rotation = (wheel_half_circumference / chasis_rotation_circle_circumference) * 360 + 45
    
    delay_time_for_full_rotation = 1.143 * (ACTUAL_MAX_SPEED / DEFAULT_SPEED)# 1.143 if speed is 50

    delay_time_for_one_pixel_movement = (beta / degrees_rotated_in_full_wheel_rotation) * delay_time_for_full_rotation # aka **magic_number**
    
    return delay_time_for_one_pixel_movement + battery_level_normalized

pixel_rotation_delay = calculate_pixel_rotation_delay()

"""
  offset: offset is a parameter that represents how many pixels we want to roughly rotate. if offset is negative, it means rotate indefinitely.
  direction: direction is a parameter that represents that direction in which we want to rotate to(i.e. right or left)
"""
def rotate(offset, direction):
    global pixel_rotation_delay
    delay = float(pixel_rotation_delay * offset)
    
    if offset >= 0:
        if direction == 'right':
            bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,rotate_right)
        else:
            bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,rotate_left)
        sleep(delay)
        bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,stop)
    else:
        if direction == 'right':
            bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,rotate_right)
        else:
            bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,rotate_left)
    
    print('rotating', offset, 'pixels to', direction)

# Automation states
LOOKING_FOR_WHITE = 0
CENTERING_WHITE = 1
APPROACHING_WHITE = 2
LOOKING_FOR_RED = 3
CENTERING_RED = 4
APPROACHING_RED = 5
NO_OPERATION = -1

automation_state = LOOKING_FOR_WHITE

def run_autonomous_sequence():

    global automation_state
    global pixel_rotation_delay
    global x_center_of_cup_previous
    global cup_not_detected_counter

    direction_to_look = 'right'
    while True:
        
        cups_detected = 0
        red_cups = 0
        non_red_cups = 0
        if automation_state == LOOKING_FOR_WHITE or automation_state == LOOKING_FOR_RED:
            look_for_cup(direction_to_look)
            request_report(10)
            for i in range(10):
                cup_detected = shared_mem.buf[i * REPORT_SIZE + CUP_DETECTION_FLAG]
                cup_color = shared_mem.buf[i * REPORT_SIZE + CUP_COLOR_CLASS_INDEX]
                if cup_detected == 1:
                    cups_detected += 1
                    if cup_color == 1:
                        red_cups += 1
                    else:
                        non_red_cups += 1
                        
            if cups_detected > 6 and non_red_cups > 6 and automation_state == LOOKING_FOR_WHITE:
                stop_robot()
                automation_state = CENTERING_WHITE
                sleep(0.4)
            elif cups_detected > 6 and red_cups > 6 and automation_state == LOOKING_FOR_RED:
                stop_robot()
                automation_state = CENTERING_RED
                sleep(0.4)
        
        # Centering the cup 
        if automation_state == CENTERING_WHITE or automation_state == CENTERING_RED:
            request_report(1)
            
            x_center_of_cup = shared_mem.buf[X_CENTER_INDEX]
            cup_detected = shared_mem.buf[CUP_DETECTION_FLAG]
            print(x_center_of_cup)
            
            # Center is image_size/2 ( image is image_size x image_size pixels), we want the cup to be in the center of the image so we can approach it.
            x_center_of_image = image_size // 2
            tolerance = 5   
            
            if x_center_of_cup == x_center_of_cup_previous and cup_detected == 0:
                print('Lost cup, rotating back to where it was.')
                
                #if we lost the cup while trying to rotate to left to center it, it means we have to rotate right to find it, and vice versa.
                if x_center_of_cup < x_center_of_image:
                    direction_to_look = 'right'
                elif x_center_of_cup > x_center_of_image:
                    direction_to_look = 'left'
                    
                """
                  if we are in automation state CENTERING_WHITE, it means we have to look for the white cup, so we switch back to automation state LOOKING_FOR_WHITE, but if we were in automation state CENTERING_RED
                  it means we were looking for the red cup, so we have to switch to automation state LOOKING_FOR_RED.   
                """
                if automation_state == CENTERING_WHITE:
                    automation_state = LOOKING_FOR_WHITE
                else:
                    automation_state = LOOKING_FOR_RED
                continue
            print(x_center_of_cup, x_center_of_image)
            if x_center_of_cup < x_center_of_image - tolerance:
                offset = x_center_of_image - x_center_of_cup
                rotate(offset, 'left')
                sleep(1)
            elif x_center_of_cup > x_center_of_image + tolerance: 
                offset = x_center_of_cup - x_center_of_image    
                rotate(offset, 'right')
                sleep(1)
            elif automation_state == CENTERING_WHITE:
                print('now approach')
                automation_state = APPROACHING_WHITE
            else:
                # automation_state = CENTERING_RED if we reach this condition
                automation_state = APPROACHING_RED
            x_center_of_cup_previous = x_center_of_cup
            
        if automation_state == APPROACHING_WHITE or automation_state == APPROACHING_RED:
            request_report(1)
            
            cup_relative_size = struct.unpack('d', shared_mem.buf[RELATIVE_SIZE_INDEX_START : RELATIVE_SIZE_INDEX_END])[0]
            tolerance = 0.01
            print(cup_relative_size, cup_relative_size - tolerance)
            
            cup_detected = shared_mem.buf[CUP_DETECTION_FLAG] 
            
            if cup_detected == 0:
                cup_not_detected_counter += 1
            
            if cup_not_detected_counter == 2:
                print('lost cup, looking for it again.')
                if automation_state == APPROACHING_WHITE:
                    automation_state = CENTERING_WHITE
                else:
                    automation_state = CENTERING_RED
                
                cup_not_detected_counter = 0
                
            if automation_state == APPROACHING_WHITE:
                cup_grab_relative_size = GRAB_SIZE_WHITE
            else:
                cup_grab_relative_size = GRAB_SIZE_RED
            
            if cup_relative_size > cup_grab_relative_size - tolerance and cup_relative_size < cup_grab_relative_size + tolerance:
                if automation_state == APPROACHING_WHITE:
                    stop_robot()
                    """TO-DO: Grab the cup and move a bit backward"""
                    grab_cup_ready = False
                    x_center_of_cup = shared_mem.buf[X_CENTER_INDEX]
                    x_center_of_image = image_size // 2
                    tolerance = 5
                    print(x_center_of_cup, x_center_of_image)
                    if  x_center_of_cup < x_center_of_image - tolerance:
                        offset = x_center_of_image - x_center_of_cup
                        rotate(offset, 'left')
                        sleep(0.5)
                    elif x_center_of_cup > x_center_of_image + tolerance:
                        offset = x_center_of_cup - x_center_of_image
                        rotate(offset, 'right')
                        sleep(0.5)
                    else:
                        grab_cup_ready = True
                    if grab_cup_ready:
                        reach_for_cup(set_top_servo = True)
                        sleep(1)
                        move_robot('forward', 0.7) 
                        grab_cup()
                        sleep(1)
                        move_robot('backward', 0.3)
                        automation_state = LOOKING_FOR_RED
                else:
                    #automation_state = APPROACHING_RED if we reach this condition
                    """TO-DO: Pour cup and put it back and move a bit backwards"""
                    stop_robot()
					# Rotating the robot by exactly quarter of the image size, since the cup is in the center of the image, rotating 4th of the image is perfect to pour the cup.
                    rotate(image_size/4, 'left')
                    pour_cup()
                    sleep(7)
                    rotate(image_size/2, 'left')
                    put_cup()
                    move_robot('backward', movement_time = 1)
                    initial_pos()
                    automation_state = NO_OPERATION
                    
            elif cup_relative_size < cup_grab_relative_size - tolerance:
                mapped_speed = int( ((EFFECTIVE_MAX_SPEED - MIN_SPEED) * math.pow((cup_relative_size - cup_grab_relative_size) / (-cup_grab_relative_size), 0.8) ) / 1.5)
                move_robot('forward', speed=mapped_speed)
            else:
                movement_t = ((cup_relative_size - cup_grab_relative_size) / (1 - cup_grab_relative_size)) * 2
                move_robot('backward', movement_t)
                sleep(0.4)

def main():
    try:
        run_autonomous_sequence()
    finally:
        shared_mem.close()  
        shared_mem.unlink()

if __name__ == '__main__':
    main()