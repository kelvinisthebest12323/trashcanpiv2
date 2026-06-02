from gpiozero import OutputDevice
import spidev
import time
import cv2
import numpy as np

# ── Pins & SPI (same as your code) ────────────────────────────────────
DIR_PIN  = OutputDevice(2,  initial_value=False)
STEP_PIN = OutputDevice(3,  initial_value=False)
CS_PIN   = OutputDevice(25, initial_value=True)

spi = spidev.SpiDev()
spi.open(0, 1)
spi.max_speed_hz = 500000
spi.mode = 1

WR      = 0x80
REG_CR0 = 0x01
REG_CR1 = 0x02
REG_CR2 = 0x03
REG_CR3 = 0x09

def write_reg(reg, value):
    CS_PIN.off(); time.sleep(0.000001)
    spi.xfer2([WR | reg, value])
    time.sleep(0.000001); CS_PIN.on()

def reset_settings():
    for r in [REG_CR0, REG_CR1, REG_CR2, REG_CR3]:
        write_reg(r, 0x00)

def set_current_milliamps(ma):
    table = [
        (100,0x00),(174,0x01),(343,0x02),(490,0x03),(530,0x04),
        (680,0x05),(770,0x06),(870,0x07),(1000,0x08),(1060,0x09),
        (1190,0x0A),(1260,0x0B),(1400,0x0C),(1490,0x0D),(1680,0x0E),
        (1800,0x0F),(1980,0x10),(2100,0x11),(2360,0x12),(2500,0x13),
    ]
    code = min(table, key=lambda x: abs(x[0]-ma))[1]
    write_reg(REG_CR1, code & 0x1F)

def set_step_mode(microsteps):
    modes = {1:0b000,2:0b001,4:0b010,8:0b011,16:0b100,32:0b101,64:0b110,128:0b111}
    write_reg(REG_CR0, modes.get(microsteps, 0b100))

def enable_driver():
    write_reg(REG_CR2, 0x80)

def set_direction(forward):
    DIR_PIN.on() if forward else DIR_PIN.off()
    time.sleep(0.000001)

def step(delay=0.0002):
    STEP_PIN.on();  time.sleep(0.000003)
    STEP_PIN.off(); time.sleep(0.000003)
    time.sleep(delay)

# ── Motor setup ───────────────────────────────────────────────────────
CS_PIN.on(); time.sleep(0.001)
reset_settings()
set_current_milliamps(1200)
set_step_mode(16)
enable_driver()

# ── Camera ────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
FRAME_CX = 320   # horizontal center of frame

LOWER_HSV = np.array([18, 90,  120])
UPPER_HSV = np.array([28, 240, 210])
MIN_RADIUS = 10   # ignore tiny blobs

def detect_ball(frame):
    """Returns (cx, cy, radius) of the largest blob, or None."""
    hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_HSV, UPPER_HSV)
    mask = cv2.erode(mask,  None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    ((cx, cy), radius) = cv2.minEnclosingCircle(c)
    if radius < MIN_RADIUS:
        return None
    return int(cx), int(cy), int(radius)

# HSV diagnostic — remove once calibrated
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    region = hsv_frame[max(0,int(cy)-10):int(cy)+10, max(0,int(cx)-10):int(cx)+10]
    if region.size > 0:
        m = region.mean(axis=(0,1))
        print(f"Ball HSV≈ H:{m[0]:.0f} S:{m[1]:.0f} V:{m[2]:.0f}  radius={int(radius)}")

# ── Tracking parameters ───────────────────────────────────────────────
DEAD_ZONE   = 30    # pixels — don't move if ball is this close to center
STEPS_SLOW  = 2     # steps per loop when close
STEPS_FAST  = 8     # steps per loop when far
FAR_THRESH  = 100   # pixels error threshold for fast mode

print("Tracking started. Press Ctrl+C to stop.")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        result = detect_ball(frame)

        if result is None:
            # No ball found — hold position
            time.sleep(0.02)
            continue

        cx, cy, radius = result
        error = cx - FRAME_CX   # positive = ball is right of center

        if abs(error) <= DEAD_ZONE:
            time.sleep(0.005)
            continue

        # Choose speed based on how far off-center the ball is
        n_steps = STEPS_FAST if abs(error) > FAR_THRESH else STEPS_SLOW
        move_right = error > 0   # if ball is right of center, move right

        set_direction(move_right)
        for _ in range(n_steps):
            step(delay=0.0001)   # faster than your original loop

except KeyboardInterrupt:
    print("Stopped")
    cap.release()
    spi.close()
    DIR_PIN.close(); STEP_PIN.close(); CS_PIN.close()
