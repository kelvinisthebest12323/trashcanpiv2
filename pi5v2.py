from gpiozero import OutputDevice
import spidev
import time

# ── Pins (BCM numbering) ──────────────────────────────────────────────
DIR_PIN  = OutputDevice(2,  initial_value=False)  # GPIO2,  physical pin 3
STEP_PIN = OutputDevice(3,  initial_value=False)  # GPIO3,  physical pin 5
CS_PIN   = OutputDevice(25, initial_value=True)   # GPIO25, physical pin 22

# ── SPI ───────────────────────────────────────────────────────────────
spi = spidev.SpiDev()
spi.open(0, 1)             # CE1 so spidev doesn't fight over GPIO8
spi.max_speed_hz = 500000
spi.mode = 1               # AMIS-30543 requires Mode 1

# ── AMIS-30543 registers ──────────────────────────────────────────────
WR      = 0x80
REG_CR0 = 0x01
REG_CR1 = 0x02
REG_CR2 = 0x03
REG_CR3 = 0x09

def write_reg(reg, value):
    CS_PIN.off()
    time.sleep(0.000001)
    spi.xfer2([WR | reg, value])
    time.sleep(0.000001)
    CS_PIN.on()

def reset_settings():
    write_reg(REG_CR0, 0x00)
    write_reg(REG_CR1, 0x00)
    write_reg(REG_CR2, 0x00)
    write_reg(REG_CR3, 0x00)

def set_current_milliamps(ma):
    table = [
        (100,  0x00), (174,  0x01), (343,  0x02), (490,  0x03),
        (530,  0x04), (680,  0x05), (770,  0x06), (870,  0x07),
        (1000, 0x08), (1060, 0x09), (1190, 0x0A), (1260, 0x0B),
        (1400, 0x0C), (1490, 0x0D), (1680, 0x0E), (1800, 0x0F),
        (1980, 0x10), (2100, 0x11), (2360, 0x12), (2500, 0x13),
    ]
    code = min(table, key=lambda x: abs(x[0] - ma))[1]
    write_reg(REG_CR1, code & 0x1F)

def set_step_mode(microsteps):
    modes = {1: 0b000, 2: 0b001, 4: 0b010, 8: 0b011,
             16: 0b100, 32: 0b101, 64: 0b110, 128: 0b111}
    write_reg(REG_CR0, modes.get(microsteps, 0b100))

def enable_driver():
    write_reg(REG_CR2, 0x80)

def set_direction(forward):
    time.sleep(0.000001)
    DIR_PIN.on() if forward else DIR_PIN.off()
    time.sleep(0.000001)

def step():
    STEP_PIN.on()
    time.sleep(0.000003)
    STEP_PIN.off()
    time.sleep(0.000003)
    time.sleep(0.000250)   # speed throttle

# ── Setup ─────────────────────────────────────────────────────────────
CS_PIN.on()
time.sleep(0.001)
reset_settings()
set_current_milliamps(1200)
set_step_mode(16)
enable_driver()

# ── Main loop ─────────────────────────────────────────────────────────
try:
    while True:
        set_direction(True)
        for _ in range(10000):
            step()
        time.sleep(0.1)

        set_direction(False)
        for _ in range(10000):
            step()
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Stopped")
    spi.close()
    DIR_PIN.close()
    STEP_PIN.close()
    CS_PIN.close()
