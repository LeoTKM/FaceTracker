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
        if (self.MI != 0 and self.MI != 1):
            print(self.MI)
            print("invalid motor index")

        # hardware pins
        self.SPI_direction_PIN = [23, 24]   # needs to be checked
        self.SPI_PWM_PIN = [18, 13]

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


motor = MotorControl(0)
motor1 = MotorControl(1)
motor.update_motor_speed(200)
motor1.update_motor_speed(100)
while (True):
    time.sleep(2)
    motor.change_dir(0)
    motor1.change_dir(0)
    time.sleep(2)
    motor.change_dir(1)
    motor1.change_dir(1)
