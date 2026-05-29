from machine import Pin, SPI
import time

DIR_PIN  = Pin(2,  Pin.OUT, value=0)
STEP_PIN = Pin(3,  Pin.OUT, value=0)
CS_PIN   = Pin(8,  Pin.OUT, value=1)

spi = SPI(0,
          baudrate=500_000,
          polarity=0,
          phase=1,
          sck=Pin(11),
          mosi=Pin(10),
          miso=Pin(9))

WR       = 0x80
REG_CR0  = 0x01
REG_CR1  = 0x02
REG_CR2  = 0x03
REG_CR3  = 0x09

def write_reg(reg, value):
    CS_PIN.value(0)
    time.sleep_us(1)
    spi.write(bytes([WR | reg, value]))
    time.sleep_us(1)
    CS_PIN.value(1)

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
    write_reg(REG_CR1, (code & 0x1F))

def set_step_mode(microsteps):
    modes = {1: 0b000, 2: 0b001, 4: 0b010, 8: 0b011,
             16: 0b100, 32: 0b101, 64: 0b110, 128: 0b111}
    write_reg(REG_CR0, modes.get(microsteps, 0b100))

def enable_driver():
    write_reg(REG_CR2, 0x80)

def set_direction(forward: bool):
    time.sleep_us(1)
    DIR_PIN.value(1 if forward else 0)
    time.sleep_us(1)

def step(delay_us):
    STEP_PIN.value(1)
    time.sleep_us(3)
    STEP_PIN.value(0)
    time.sleep_us(3)
    if delay_us > 0:
        time.sleep_us(delay_us)

# ── Setup ─────────────────────────────────────────────────────────────
CS_PIN.value(1)
time.sleep_ms(1)
reset_settings()
set_current_milliamps(1200)
set_step_mode(16)
enable_driver()

# ── Speed map: name → delay in microseconds between steps ────────────
SPEEDS = {
    "1": ("Slow",    800),
    "2": ("Medium",  400),
    "3": ("Fast",    150),
    "4": ("Max",      50),   # push the limit — see note below
}

# ── Main interactive loop ─────────────────────────────────────────────
print("AMIS-30543 Stepper Controller")
print("================================")

while True:
    # --- Direction ---
    print("\nDirection:")
    print("  f = Forward")
    print("  b = Backward")
    d = input(">> ").strip().lower()
    if d not in ("f", "b"):
        print("Invalid — type f or b")
        continue
    forward = (d == "f")

    # --- Speed ---
    print("\nSpeed:")
    for k, (name, delay) in SPEEDS.items():
        print(f"  {k} = {name}  ({delay}µs delay)")
    s = input(">> ").strip()
    if s not in SPEEDS:
        print("Invalid — pick 1-4")
        continue
    speed_name, delay_us = SPEEDS[s]

    print(f"\nRunning {speed_name} {'Forward' if forward else 'Backward'} — Ctrl+C to stop\n")

    set_direction(forward)
    try:
        while True:
            step(delay_us)
    except KeyboardInterrupt:
        print("\nStopped.")
