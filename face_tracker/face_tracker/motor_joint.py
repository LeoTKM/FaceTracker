# @brief Motor control (low & high level)
#
# @author Leo
#
# Contact leowang657@gmail.com

# first work with the camera
# once everything work, test it with the encoder. 

# -- ROS2 -- 
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import ExternalShutdownException
from rclpy.executors import MultiThreadedExecutor
import threading

# -- Message types --
from std_msgs.msg import String
from face_messages.msg import MotorPWM, Boundary
from face_messages.srv import Angles

import time
import logging

# -- Constant --
KP = 400
PWM_MAX = 2240
PWM_MIN = 1

# -- Raspberry Pi -- 
import lgpio
h = lgpio.gpiochip_open(0)


class MotorControl():
    # low-level motor control logic
    def __init__(self, motor_index: int):
        self.MI = motor_index
        if (self.MI != 0 or self.MI != 1):
            self.get_logger().error(f"{self.MI} is an invalid index")

        # hardware pins
        self.SPI_direction_PIN = [23, 24]   # needs to be checked
        self.SPI_PWM_PIN = [18, 14]

        lgpio.gpio_claim_output(h, self.SPI_direction_PIN[motor_index])
        lgpio.gpio_claim_output(h, self.SPI_PWM_PIN[motor_index])

 
    def update_motor_speed(self, frequency):
        # ensure PWM not too fast
        frequency = frequency if frequency < PWM_MAX else PWM_MAX
        frequency = frequency if frequency > PWM_MIN else PWM_MIN

        lgpio.tx_pwm(h, self.SPI_PWM_PIN[self.MI], frequency, 50) # duty cycle = 50%


    def change_dir(self, dir: int):
        # 1 is ...
        lgpio.gpio_write(h, self.SPI_direction_PIN[self.MI], dir)


class MotorJointNode(Node):
    # subscribes to PWM output from the processor node
    def __init__(self, motor_index: int):
        super().__init__(f'motor_joint_{motor_index}')
        self.MI = motor_index
        # motor_index: 0, 1 corresponding to motor joint 1 and joint 2
        self.resting_angles: list[float] = [120.0, 120.0] # fixed
        self.current_angles: list[float] = [0, 0]       # from return_angles (service)
        self.out_of_bound: list[bool] = [False, False]  # from /angle_boundary_check
        self.target_PWM: list[int] = [0, 0]             # from /PWM_command
        self.target_dir: list[int] = [0, 0]             # 0 or 1, from /PWM_command

        self.motor_instance = MotorControl(motor_index)
        
        self.zeroed_j1 = False     
        self.zeroed_j2 = False          

        self.lock = threading.Lock()

        # client setup
        self.angle_client = self.create_client(Angles, 'return_angles')
        self.request_package = Angles.Request()

        # the following while loop WILL BLOCK the execution of the other node...
        # but it's fine, because both nodes subscribe to the same service
        while not self.angle_client.wait_for_service(timeout_sec = 1):
            self.get_logger().info("magnetic encoder not available, retrying...")

        # start reading angles from the i2c_manager node immediately (calling services)
        group_a = MutuallyExclusiveCallbackGroup()
        self.angle_timer = self.create_timer(0.02, self.update_current_angles, callback_group = group_a)

        # 2 subscriptions: /angle_boundary_check & /PWM_command
        group_b = MutuallyExclusiveCallbackGroup()
        group_c = MutuallyExclusiveCallbackGroup()
        self.out_of_bound_subscriber = self.create_subscription(Boundary, '/angle_boundary_check', self.update_boundary, 10, callback_group = group_b)
        self.PWM_subscriber = self.create_subscription(MotorPWM, '/PWM_command', self.update_target_PWM, 10, callback_group = group_c)
        
        # zeroing the motors
        # reading angles and zeroing the motors happen at the same time
        self.zero_thread = threading.Thread(target=self.zero_motor, daemon=True)
        self.zero_thread.start()

        group_d = MutuallyExclusiveCallbackGroup()
        self.timer = self.create_timer(0.02, self.run_project, callback_group = group_c)


    def update_current_angles(self) -> None:
        # constantly updating the motors angle orientations
        match self.MI:
            # check which motor
            case 0:
                 self.request_package.zeroed_j1 = self.zeroed_j1
                 self.request_package.zeroed_j2 = True 
            case 1:
                self.request_package.zeroed_j1 = True
                self.request_package.zeroed_j2 = self.zeroed_j2
        
        future = self.angle_client.call_async(self.request_package)
        # there would be deadlocks if handled using the .spin method
        # system gets stuck after the second motor node makes its first request
        future.add_done_callback(self.handle_angle_response)
       

    def handle_angle_response(self, future) -> None:
        response = future.result()

        if (response == None):
            self.get_logger().info("magnetic encoder not available...")
            return

        with self.lock:
            match self.MI:
                case 0:
                    self.current_angles[0] = response.angle_j1
                case 1:
                    self.current_angles[1] = response.angle_j2
        return 


    def zero_motor(self):
        while (True):
            with self.lock:
                current_angle = self.current_angles[self.MI]

            if (abs(current_angle - self.resting_angles[self.MI]) < 4):
                # zeroed
                self.get_logger().info(f"Motor {self.MI} zeroed")
                self.zeroed_j1 = self.zeroed_j2 = True
                self.angle_timer.cancel()
                return
            
            delta_angle = current_angle - self.resting_angles[self.MI]
            target_PWM = abs(self.compute_PID(delta_angle))
            target_dir = -1 if (delta_angle > 0) else 1
            #... move motor


    def compute_PID(self, angle_error: int) -> int:
        p_t = angle_error * KP
        i_t = 0
        d_t = 0
        return p_t + i_t + d_t


    def update_boundary(self, msg):
        # from /angle_boundary_check
        if (msg == None):
            self.get_logger().info("magnetic encoder is not available...")
        with self.lock:
            match self.MI:
                case 0:
                    self.out_of_bound[self.MI] = msg.j1_out_of_bound
                case 1: 
                    self.out_of_bound[self.MI] = msg.j2_out_of_bound

        print(msg.j1_out_of_bound)
        return
        

    def update_target_PWM(self, msg):
        # from /PWM_command
        if (msg == None):
            self.get_logger().info("the camera is not available...")
        with self.lock:
            self.target_PWM[0] = msg.pwm_j1
            self.target_PWM[1] = msg.pwm_j2
            self.target_dir[0] = msg.dir_j1
            self.target_dir[1] = msg.dir_j2
        return
    

    def run_project(self):
        # we shouldn't start following the face if the zeroing process is not complete
        if not (self.zeroed_j2 and self.zeroed_j1): return

        # assuming
        # self.target_PWM[self.MI] has the latest PWM command
        # self.target_dir[self.MI] has the latest direction command
        # self.out_of_bound[self.MI] tells us if the motors are running properly

        # if the motor exceeds angle constraints
        if self.out_of_bound[self.MI]:
            self.motor_instance.update_motor_speed(0)

        self.motor_instance.update_motor_speed(self.target_PWM[self.MI])
        self.motor_instance.change_dir(self.target_dir[self.MI])
        

def main(args=None):
    rclpy.init(args=args)

    motor_one = MotorJointNode(0) 
    motor_two = MotorJointNode(1)

    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(motor_one)
    executor.add_node(motor_two)
    executor.spin()

    executor.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
