# @brief Motor control
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

KP = 400

class MotorControl():
    # low-level motor control logic
    def temp():
        return

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
        
        self.zeroed_j1 = False     
        self.zeroed_j2 = False          

        self.lock = threading.Lock()

        # client setup
        self.angle_client = self.create_client(Angles, 'return_angles')
        self.request_package = Angles.Request()
        self.get_logger().info(f"HELLO World, from {self.MI}")

        # the following while loop WILL BLOCK the execution of the other node...
        while not self.angle_client.wait_for_service(timeout_sec = 1):
            self.get_logger().info("magnetic encoder not available, retrying...")

        # start reading angles from the i2c_manager node immediately (calling services)
        group_a = MutuallyExclusiveCallbackGroup()
        self.angle_timer = self.create_timer(0.02, self.update_current_angles, callback_group = group_a)

        # reading angles and zeroing the motors happen at the same time
        self.zero_thread = threading.Thread(target=self.zero_motor, daemon=True)
        self.zero_thread.start()


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
                self.angle_timer.cancel()
                return
            
            delta_angle = current_angle - self.resting_angles[self.MI]
            target_PWM = abs(self.compute_PID(delta_angle))
            target_dir = -1 if (delta_angle > 0) else 1
            #...


    def compute_PID(self, angle_error: int) -> int:
        p_t = angle_error * KP
        i_t = 0
        d_t = 0
        return p_t + i_t + d_t


    def update_boundary(self):
        # for self.out_of_bound

        return
        

    def update_target_PWM(self):
        # for self.target_PWM
        return
        

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


# h = lgpio.gpiochip_open(0)

# PWM_MAX = 2240
# PWM_MIN = 1

# def check_angle_boundary(angles):
#     for angle in angles:
#         if not (0 <= angle and angle <= 360):
#             return False
#     return True


# class Motor:
#     def __init__ (
#         self, MAX_ANGLE: float, MIN_ANGLE: float, INIT_ANGLE: float,
#         I2C_op: int, SPI_dir_PIN: int, SPI_PWM_PIN: int
#     ):
#         if (not (check_angle_boundary([MAX_ANGLE, MIN_ANGLE, INIT_ANGLE]))):
#             raise ValueError("invalid angle")

#         self.MAX_ANGLE = MAX_ANGLE
#         self.MIN_ANGLE = MIN_ANGLE
#         self.INIT_ANGLE = INIT_ANGLE

#         self.SPI_dir_PIN = SPI_dir_PIN              # SPI pins
#         self.SPI_PWM_PIN = SPI_PWM_PIN

#         lgpio.gpio_claim_output(h, SPI_dir_PIN)     # initialize SPI pins
#         lgpio.gpio_claim_output(h, SPI_PWM_PIN)

#         self.encoder = ME.MagneticEncoder(I2C_op)   # assign an angle sensor to the motor


#     def update_motor_speed(self, frequency):
#         if frequency >= PWM_MAX:
#             frequency = PWM_MAX
#         elif frequency <= PWM_MIN:
#             frequency = PWM_MIN
#         lgpio.tx_pwm(h, self.SPI_PWM_PIN, frequency, 50)


#     def change_dir(self, dir: int):
#         lgpio.gpio_write(h, self.SPI_dir_PIN, dir)


#     async def angle_violation(self):
#         current_angle = await self.encoder.return_angle()
#         if not (MIN_ANGLE <= current_angle and current_angle <= MAX_ANGLE):
#             lgpio.tx_pwm(h, self.SPI_PWM_PIN, 0, 50)    # stop motion


#     async def initialize_position(self):
#         target_angle = self.INIT_ANGLE

#         while (True):
#             await asyncio.sleep(0.001)
#             current_angle = await self.encoder.return_angle()
#             error = target_angle - current_angle
#             print(error, target_angle, current_angle)

#             if (abs(error) <= 1):
#                 self.update_motor_speed(0)   # stop calibrating
#                 print("arm ready")
#                 break

#             update_frequency = PID.compute_PID(error)

#             if update_frequency <= 0:
#                 lgpio.gpio_write(h, self.SPI_dir_PIN, 1)
#             else:
#                 lgpio.gpio_write(h, self.SPI_dir_PIN, 0)
            
#             self.update_motor_speed(abs(update_frequency))


# async def testing():
#     testing_motor = Motor(360, 0, 120, 1, 1, 1)
#     await testing_motor.initialize_position()

# if __name__ == "__main__":
#     asyncio.run(testing())