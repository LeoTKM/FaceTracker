# @brief Reads face shift and publishes the PWM output to the motors
#
# @author Leo
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
from face_messages.msg import FaceShift, MotorPWM 

import logging
import time

# -- PID Constant --
KP = 50

class Processor(Node):
    def __init__(self):
        super().__init__('processor')
        
        self.delta_x = 0
        self.delta_y = 0
        self.init_done = False

        # concurrency is needed
        # and thus thread protection is required
        group_a = MutuallyExclusiveCallbackGroup()
        group_b = MutuallyExclusiveCallbackGroup()
        self.lock = threading.Lock()

        # subscriber
        self.face_shift_subscriber = self.create_subscription(FaceShift, '/camera_data', self.update_var, 10, callback_group = group_a)

        # publisher
        # calculates and publishes the target PWM to /PWM_command every 20ms (50Hz)
        self.PWM_calculation_timer = self.create_timer(0.02, self.calculate_publish_PWM, callback_group = group_b)
        self.PWM_publisher = self.create_publisher(MotorPWM, '/PWM_command', 10, callback_group = group_b)

    
    def calculate_publish_PWM(self) -> int:
        # runs every 20ms
        with self.lock:
            check = self.init_done
        if (not check):
            # camera not ready yet
            self.get_logger().info("CAMERA NOT READY | from processor node")
            return 
        
        # testing code
        # self.get_logger().info("Camera ready and sending information")
        
        with self.lock:
            # to prevent variables from changing values while running PID
            delta_x = self.delta_x
            delta_y = self.delta_y
        
        msg = MotorPWM()
        if delta_x < 0:
            msg.dir_j1 = -1
        if delta_y < 0:
            msg.dir_j2 = -1

        msg.pwm_j1 = abs(self.compute_PID(delta_x))
        msg.pwm_j2 = abs(self.compute_PID(delta_y))
        
        self.PWM_publisher.publish(msg)


    def compute_PID(self, error: int) -> int:
        p_t = error * KP
        i_t = 0
        d_t = 0
        return p_t + i_t + d_t


    def update_var(self, msg) -> int:
        # runs everytime new subscribed information arrives (100Hz)
        with self.lock:
            self.init_done = msg.init_done
            self.delta_x = msg.delta_x
            self.delta_y = msg.delta_y


def main(args=None):
    rclpy.init(args=args)

    processing_unit = Processor() 
    executor = MultiThreadedExecutor() # mutli thread needed
    executor.add_node(processing_unit)
    executor.spin()

    rclpy.shutdown()


if __name__ == "__main__":
    main()
