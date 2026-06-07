# @brief The I2C multiplexer (TCA9548A) node for handling communication with I2C devices (ie the magnetic encoder)
#
# @author Leo
#
# @setup Only one I2C bus is available on the Pi, the physical pins are GPIO2 (SDA) and GPIO3 (SCL) (i.e., SMBus(1)).
#        MUST connect the RESET pin on the multiplexer to 3V3!
#
# Contact leowang657@gmail.com

# -- ROS2 -- 
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
import threading

# -- Message types -- 
from std_msgs.msg import String
from face_messages.msg import Boundary
from face_messages.srv import Angles

import logging
from smbus2 import SMBus, i2c_msg
import time

logging.basicConfig(level=logging.INFO)

MULTIPLEXER_ADDRESS = 0x70  # The I2C address of TCA9548A, also the address of the only availablesregister
DEVICE_ADDRESS = 0x36       # The I2C address of AS5600
ANGLE_REGISTER = 0x0E       # The ANGLE register which stores 2 Bytes 
ENCODER_RESOLUTION = 4096

class I2CManagerNode(Node):
    def __init__(self):
        super().__init__('i2c_manager')
        self.lock = threading.Lock()
        # the i2c manager first make sure that the motors are zeroed
        self.srv = self.create_service(Angles, 'return_angles', self.return_angles)

        # Boundary message type tells whether the motors are exceeding the allowed range of motion 
        self.publisher_ = self.create_publisher(Boundary, '/angle_boundary_check', 10)
        self.publish_group = MutuallyExclusiveCallbackGroup()
        # since publish_boundary_check & update_angle will run at the same time
        # note: publish_boundary_check will run after the motors are zeroed
        
        # values obtained physically
        self.max_j1 = 360    # 360 degrees
        self.min_j1 = 0      # 0 degrees

        self.max_j2 = 360
        self.min_j2 = 0

        # self.j1_rest_angle = 120 -> move to their respective nodes
        # self.j2_rest_angle = 120

        self.j1_out_of_bound = False
        self.j2_out_of_bound = False

        self.angles: list[float] = [0.0, 0.0]
        self.i2c_channels = [0, 1] # TCA9548A has 8 channels (0-7), each channel is physically connected to an I2C device

        # start reading the angles immediately
        self.encoder_thread = threading.Thread(target=self.update_angle, daemon=True)
        self.encoder_thread.start()


    def return_angles(self, request, response):
        if (request.zeroed_j1 and request.zeroed_j2):
            # if motors are zeroed
            # start checking whether the motors are exceeding the allowed range of motion
            # run publish_boundary_check every 30 ms (i.e, ~30 Hz to match with the camera 30 fps) 
            self.boundary_timer = self.create_timer(0.03, self.publish_boundary_check, callback_group = self.publish_group)
            response.angle_j1 = response.angle_j2 = -100
            return response
        else:
            with self.lock:
                response.angle_j1 = self.angles[0]
                response.angle_j2 = self.angles[1]
            
            print(f"from client: {request.zeroed_j1} and {request.zeroed_j2}")
            return response


    def publish_boundary_check(self):
        msg = Boundary()
        with self.lock:
            if (self.min_j1 > self.angles[0] or self.max_j1 < self.angles[0]):
                msg.j1_out_of_bound = True
            if (self.min_j2 > self.angles[1] or self.max_j2 < self.angles[1]):
                msg.j2_out_of_bound = True

        self.publisher_.publish(msg)
        

    def update_angle(self) -> None:
        # run at start
        while True:
            with self.lock:
                self.angles[0] = self.read_angle(0)
                self.angles[1] = self.read_angle(1)


    def read_angle(self, i2c_channel: int) -> float:
        with SMBus(1) as bus:
            # The angle register is 12 bit long, ie:
            # A[11:8] B[7:0]
            # AAAABBBBBBBB
            channel_mask = 1 << i2c_channel # read their datasheet
            print(channel_mask)
            bus.write_byte(0x70, channel_mask)
            time.sleep(0.01)

            (A_byte, B_byte) = bus.read_i2c_block_data(DEVICE_ADDRESS, ANGLE_REGISTER, 2)
            resolution = (A_byte << 8) | B_byte

            angle = resolution * 360 / ENCODER_RESOLUTION

            bus.write_byte(0x70, 0x00) # close channel
            return angle


def main(args=None):
    rclpy.init(args=args)

    encoders = I2CManagerNode() # single thread is sufficient since it's only publishing messages. 

    executor = MultiThreadedExecutor() # mutli thread needed
    executor.add_node(encoders)
    executor.spin()

    rclpy.shutdown()


if __name__ == "__main__":
    main()