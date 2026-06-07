import logging
from smbus2 import SMBus, i2c_msg
import time

MULTIPLEXER_ADDRESS = 0x70  # The I2C address of TCA9548A, also the address of the only availablesregister
DEVICE_ADDRESS = 0x36       # The I2C address of AS5600
ANGLE_REGISTER = 0x0E       # The ANGLE register which stores 2 Bytes 

ENCODER_RESOLUTION = 4096

def read_angle():
    # run this on individual I2C devices to verify hardware connections
    with SMBus(1) as bus:
        (A_byte, B_byte) = bus.read_i2c_block_data(DEVICE_ADDRESS, ANGLE_REGISTER, 2)
        resolution = (A_byte << 8) | B_byte

        angle = resolution * 360 / ENCODER_RESOLUTION
        print(angle)

read_angle()