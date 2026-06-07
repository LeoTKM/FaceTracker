# Test individual motor setup by running this file. 
# PWM or STEP output configurable

import time
import lgpio
import asyncio

# -- Raspberry Pi 4 -- 
# Motor one
PWM_0 = 18          # PWM0, pin 18
DIR_0 = 23          # GPIO pin 23, direction 

# Motor two
PWM_1 = 13          # PWM1, pin 13
DIR_1 = 24          # GPIO pin 24, direction 
STEP_GPIO = 25      # GPIO pin 25, step

# Initiate GPIOs
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, DIR_0)
lgpio.gpio_claim_output(h, DIR_1)
lgpio.gpio_claim_output(h, STEP_GPIO)
lgpio.gpio_claim_output(h, PWM_0)
lgpio.gpio_claim_output(h, PWM_1)

# dir = 1: left
# dir = 0: right

async def oscillate(stp: int, use_pwm: bool = False, PWM_PIN: int = 0, STEP_PIN: int = 0, DIR_PIN: int = 0):
    match use_pwm:
        case True:
            lgpio.gpio_write(h, DIR_PIN, 1)
            lgpio.tx_pwm(h, PWM_PIN, 500, 50) 
            time.sleep(10)
            lgpio.tx_pwm(h, PWM_PIN, 0, 50)
            
            lgpio.gpio_write(h, DIR_PIN, 0)
            lgpio.tx_pwm(h, PWM_PIN, 500, 50)
            time.sleep(10)
            lgpio.tx_pwm(h, PWM_PIN, 0, 50)

        case False:
            lgpio.gpio_write(h, DIR_PIN, 1)
            for i in range(stp):
                lgpio.gpio_write(h, STEP_PIN, 1)
                time.sleep(0.001)
                lgpio.gpio_write(h, STEP_PIN, 0)
                time.sleep(0.001)
            time.sleep(1)
            lgpio.gpio_write(h, DIR_PIN, 0)
            for i in range(stp):
                lgpio.gpio_write(h, STEP_PIN, 1)
                time.sleep(0.001)
                lgpio.gpio_write(h, STEP_PIN, 0)
                time.sleep(0.001)


if __name__ == "__main__":
    print("Testing")
    while (1):
        # -- test two motors --  
        asyncio.run(oscillate(100, True, PWM_1, DIR_1))

        # for PWM test, uncomment the next line
        # asyncio.run(oscillate(200, use_pwm=True))