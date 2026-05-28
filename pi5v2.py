import RPi.GPIO as GPIO
import spidev
import time

# ── Pin setup (BCM numbering) ─────────────────────────────────────────
DIR_PIN  = 2
STEP_PIN = 3

GPIO.setmode(GPIO.BCM)
GPIO.setup(DIR_PIN,  GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(STEP_PIN, GPIO.OUT, initial=GPIO.LOW)

spi = spidev.SpiDev()
spi.open(0, 0)          # bus 0, CE0 = GPIO8
spi.max_speed_hz = 500_000
spi.mode = 0b01         # SPI Mode 1

# ── AMIS-30543 register map ───────────────────────────────────────────
WR      = 0x80
REG_CR0 = 0x01
REG_CR1 = 0x02
REG_CR2 = 0x03
REG_CR3 = 0x09

def write_reg(reg, value):
    spi.xfer2([WR | reg, value])

def reset_settings():
    for reg in [REG_CR0, REG_CR1, REG_CR2, REG_CR3]:
        write_reg(reg, 0x00)

def set_current_milliamps(ma):
    table = [
        (100,0x00),(174,0x01),(343,0x02),(490,0x03),(530,0x04),
        (680,0x05),(770,0x06),(870,0x07),(1000,0x08),(1060,0x09),
        (1190,0x0A),(1260,0x0B),(1400,0x0C),(1490,0x0D),(1680,0x0E),
        (1800,0x0F),(1980,0x10),(2100,0x11),(2360,0x12),(2500,0x13),
    ]
    code = min(table, key=lambda x: abs(x[0] - ma))[1]
    write_reg(REG_CR1, code & 0x1F)

def set_step_mode(microsteps):
    modes = {1:0b000,2:0b001,4:0b010,8:0b011,16:0b100,32:0b101,64:0b110,128:0b111}
    write_reg(REG_CR0, modes.get(microsteps, 0b100))

def enable_driver():
    write_reg(REG_CR2, 0x80)

def set_direction(forward: bool):
    GPIO.output(DIR_PIN, GPIO.HIGH if forward else GPIO.LOW)

def step(delay_us):
    GPIO.output(STEP_PIN, GPIO.HIGH)
    time.sleep(delay_us / 1_000_000)
    GPIO.output(STEP_PIN, GPIO.LOW)
    time.sleep(delay_us / 1_000_000)

# ── Setup ─────────────────────────────────────────────────────────────
time.sleep(0.001)
reset_settings()
set_current_milliamps(1200)
set_step_mode(16)
enable_driver()

# ── Input helpers ─────────────────────────────────────────────────────
def get_speed():
    """
    Returns delay in microseconds between steps.
    Speed range: 1 (fastest, 500us delay) to 10 (slowest, 5000us delay)
    """
    while True:
        try:
            val = int(input("Speed (1=fast → 10=slow): "))
            if 1 <= val <= 10:
                # Map 1–10 → 500us–5000us delay
                return int(500 + (val - 1) * (5000 - 500) / 9)
            print("  Please enter a number between 1 and 10.")
        except ValueError:
            print("  Numbers only please.")

def get_direction():
    while True:
        val = input("Direction (f=forward, r=reverse): ").strip().lower()
        if val in ("f", "r"):
            return val == "f"
        print("  Enter 'f' or 'r'.")

def get_steps():
    """Range: 100–50000 steps"""
    while True:
        try:
            val = int(input("Steps to run (100–50000): "))
            if 100 <= val <= 50000:
                return val
            print("  Please enter a number between 100 and 50000.")
        except ValueError:
            print("  Numbers only please.")

# ── Main loop ─────────────────────────────────────────────────────────
print("\n── AMIS-30543 Stepper Controller ──")
print("Press Ctrl+C at any time to stop.\n")

try:
    while True:
        delay_us  = get_speed()
        forward   = get_direction()
        num_steps = get_steps()

        print(f"\nRunning: {'forward' if forward else 'reverse'}, "
              f"{num_steps} steps, delay={delay_us}µs/step ...\n")

        set_direction(forward)
        for _ in range(num_steps):
            step(delay_us)

        print("Done.\n")

except KeyboardInterrupt:
    print("\nStopped.")
finally:
    spi.close()
    GPIO.cleanup()
import RPi.GPIO as GPIO
import spidev
import time

# ── Pin setup (BCM numbering) ─────────────────────────────────────────
DIR_PIN  = 2
STEP_PIN = 3

GPIO.setmode(GPIO.BCM)
GPIO.setup(DIR_PIN,  GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(STEP_PIN, GPIO.OUT, initial=GPIO.LOW)

spi = spidev.SpiDev()
spi.open(0, 0)          # bus 0, CE0 = GPIO8
spi.max_speed_hz = 500_000
spi.mode = 0b01         # SPI Mode 1

# ── AMIS-30543 register map ───────────────────────────────────────────
WR      = 0x80
REG_CR0 = 0x01
REG_CR1 = 0x02
REG_CR2 = 0x03
REG_CR3 = 0x09

def write_reg(reg, value):
    spi.xfer2([WR | reg, value])

def reset_settings():
    for reg in [REG_CR0, REG_CR1, REG_CR2, REG_CR3]:
        write_reg(reg, 0x00)

def set_current_milliamps(ma):
    table = [
        (100,0x00),(174,0x01),(343,0x02),(490,0x03),(530,0x04),
        (680,0x05),(770,0x06),(870,0x07),(1000,0x08),(1060,0x09),
        (1190,0x0A),(1260,0x0B),(1400,0x0C),(1490,0x0D),(1680,0x0E),
        (1800,0x0F),(1980,0x10),(2100,0x11),(2360,0x12),(2500,0x13),
    ]
    code = min(table, key=lambda x: abs(x[0] - ma))[1]
    write_reg(REG_CR1, code & 0x1F)

def set_step_mode(microsteps):
    modes = {1:0b000,2:0b001,4:0b010,8:0b011,16:0b100,32:0b101,64:0b110,128:0b111}
    write_reg(REG_CR0, modes.get(microsteps, 0b100))

def enable_driver():
    write_reg(REG_CR2, 0x80)

def set_direction(forward: bool):
    GPIO.output(DIR_PIN, GPIO.HIGH if forward else GPIO.LOW)

def step(delay_us):
    GPIO.output(STEP_PIN, GPIO.HIGH)
    time.sleep(delay_us / 1_000_000)
    GPIO.output(STEP_PIN, GPIO.LOW)
    time.sleep(delay_us / 1_000_000)

# ── Setup ─────────────────────────────────────────────────────────────
time.sleep(0.001)
reset_settings()
set_current_milliamps(1200)
set_step_mode(16)
enable_driver()

# ── Input helpers ─────────────────────────────────────────────────────
def get_speed():
    """
    Returns delay in microseconds between steps.
    Speed range: 1 (fastest, 500us delay) to 10 (slowest, 5000us delay)
    """
    while True:
        try:
            val = int(input("Speed (1=fast → 10=slow): "))
            if 1 <= val <= 10:
                # Map 1–10 → 500us–5000us delay
                return int(500 + (val - 1) * (5000 - 500) / 9)
            print("  Please enter a number between 1 and 10.")
        except ValueError:
            print("  Numbers only please.")

def get_direction():
    while True:
        val = input("Direction (f=forward, r=reverse): ").strip().lower()
        if val in ("f", "r"):
            return val == "f"
        print("  Enter 'f' or 'r'.")

def get_steps():
    """Range: 100–50000 steps"""
    while True:
        try:
            val = int(input("Steps to run (100–50000): "))
            if 100 <= val <= 50000:
                return val
            print("  Please enter a number between 100 and 50000.")
        except ValueError:
            print("  Numbers only please.")

# ── Main loop ─────────────────────────────────────────────────────────
print("\n── AMIS-30543 Stepper Controller ──")
print("Press Ctrl+C at any time to stop.\n")

try:
    while True:
        delay_us  = get_speed()
        forward   = get_direction()
        num_steps = get_steps()

        print(f"\nRunning: {'forward' if forward else 'reverse'}, "
              f"{num_steps} steps, delay={delay_us}µs/step ...\n")

        set_direction(forward)
        for _ in range(num_steps):
            step(delay_us)

        print("Done.\n")

except KeyboardInterrupt:
    print("\nStopped.")
finally:
    spi.close()
    GPIO.cleanup()