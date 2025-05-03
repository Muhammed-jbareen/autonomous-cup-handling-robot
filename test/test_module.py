import smbus
import time
import struct
import sys

# Set the I2C bus number, usually 1
I2C_BUS = 3

# Set the I2C address of the 4-ch encoder motor driver
MOTOR_ADDR = 0x34 

#Register address
ADC_BAT_ADDR = 0x00
MOTOR_TYPE_ADDR = 20 #Set the encoder motor type
MOTOR_ENCODER_POLARITY_ADDR = 21 #Set the polarity of the encoder
#If the motor speed can not be controlled, either rotating at the fastest speed or stopping, the value of this address can be reset
#Range: 0 or 1, default: 0
MOTOR_FIXED_PWM_ADDR = 31 #PWM(-100~100)Fixed PWM control, open-loop control, range: (-100~100)
MOTOR_FIXED_SPEED_ADDR = 51 #Fixed speed control, closed-loop control
MOTOR_ENCODER_TOTAL_ADDR = 60 #Total pulse value of each of the four encoder motors
#If the number of pulses per revolution of the motor is known as U, and the diameter of the wheel is known as D, the distance traveled by each wheel can be obtained by counting the pulses
#(P/U) * (3.14159*D) For example, if the total number of pulses for motor 1 is P, the distance traveled is (P/U) * (3.14159*D)
#The number of pulses per revolution U for different motors can be tested manually by rotating 10 revolutions and reading the pulse count, and then taking the average value to obtain


#Motor type values
MOTOR_TYPE_WITHOUT_ENCODER = 0
MOTOR_TYPE_TT = 1
MOTOR_TYPE_N20 = 2
MOTOR_TYPE_JGB37_520_12V_110RPM = 3 #Magnetic ring rotates 44 pulses per revolution, reduction ratio: 90, default

#Motor type and encoder direction polarity
MotorType = MOTOR_TYPE_JGB37_520_12V_110RPM
MotorEncoderPolarity = 0

bus = smbus.SMBus(I2C_BUS)
speed1 = [30, 30, 0, 0]
speed_test = [50, -50, 50, -50]
speed2 = [50,50,0,0]
speed3 = [0,0,0,0]

pwm1 = [100,-100,-100,100]
pwm2 = [-100,-100,-100,-100]
pwm3 = [0,0,0,0]

def Motor_Init(): #initialize motor
    bus.write_byte_data(MOTOR_ADDR, MOTOR_TYPE_ADDR, MotorType)  #Set the motor type
    time.sleep(0.5)
    bus.write_byte_data(MOTOR_ADDR, MOTOR_ENCODER_POLARITY_ADDR, MotorEncoderPolarity)  #Set the polarity of the encoder


def rotate_right():
      bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_PWM_ADDR,pwm1)

def main():

    try:
      while True:
            #battery = bus.read_i2c_block_data(MOTOR_ADDR, ADC_BAT_ADDR)
            #print("V = {0}mV".format(battery[0]+(battery[1]<<8)))
      
            Encode = struct.unpack('iiii',bytes(bus.read_i2c_block_data(MOTOR_ADDR, MOTOR_ENCODER_TOTAL_ADDR,16)))
            print("Encode1 = {0}  Encode2 = {1}  Encode3 = {2}  Encode4 = {3}".format(Encode[0],Encode[1],Encode[2],Encode[3]))
            bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,speed_test)
            time.sleep(1.143)
            bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,speed3)
            time.sleep(2)
            
            
    except KeyboardInterrupt:
          Encode = struct.unpack('iiii',bytes(bus.read_i2c_block_data(MOTOR_ADDR, MOTOR_ENCODER_TOTAL_ADDR,16)))
          print("Encode1 = {0}  Encode2 = {1}  Encode3 = {2}  Encode4 = {3}".format(Encode[0],Encode[1],Encode[2],Encode[3]))
          bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR,speed3)
          sys.exit()
          
          
if __name__ == "__main__":
    Motor_Init()
    main()
