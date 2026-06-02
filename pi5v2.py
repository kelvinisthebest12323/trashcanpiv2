import cv2
import numpy as np
from gpiozero import OutputDevice
import spidev
import time

# ============================================================
# MOTOR SETUP (UNCHANGED)
# ============================================================

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
        (100,0x00),(174,0x01),(343,0x02),(490,0x03),
        (530,0x04),(680,0x05),(770,0x06),(870,0x07),
        (1000,0x08),(1060,0x09),(1190,0x0A),(1260,0x0B),
        (1400,0x0C),(1490,0x0D),(1680,0x0E),(1800,0x0F),
        (1980,0x10),(2100,0x11),(2360,0x12),(2500,0x13),
    ]
    code = min(table, key=lambda x: abs(x[0] - ma))[1]
    write_reg(REG_CR1, code & 0x1F)

def set_step_mode(microsteps):
    modes = {1:0b000,2:0b001,4:0b010,8:0b011,16:0b100,32:0b101,64:0b110,128:0b111}
    write_reg(REG_CR0, modes.get(microsteps, 0b100))

def enable_driver():
    write_reg(REG_CR2, 0x80)

def set_direction(forward):
    DIR_PIN.on() if forward else DIR_PIN.off()

def step():
    STEP_PIN.on()
    time.sleep(0.000003)
    STEP_PIN.off()
    time.sleep(0.000250)

# ============================================================
# CAMERA + TRACKING
# ============================================================

LOWER_HSV = np.array([20, 180, 170])
UPPER_HSV = np.array([35, 255, 255])

MIN_AREA = 200
FRAME_W = 640
FRAME_CENTER_X = FRAME_W // 2
DEADBAND = 25

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ============================================================
# CLICK TO GET HSV
# ============================================================

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        frame = param
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        h, s, v = hsv[y, x]
        b, g, r = frame[y, x]

        print("\n--- CLICKED PIXEL ---")
        print(f"Position: ({x}, {y})")
        print(f"HSV: ({h}, {s}, {v})")
        print(f"BGR: ({b}, {g}, {r})")
        print("---------------------\n")

cv2.namedWindow("Tracking")

# ============================================================
# INIT MOTOR
# ============================================================

CS_PIN.on()
time.sleep(0.001)
reset_settings()
set_current_milliamps(1200)
set_step_mode(16)
enable_driver()

# ============================================================
# MAIN LOOP
# ============================================================

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.setMouseCallback("Tracking", mouse_callback, frame)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv = cv2.GaussianBlur(hsv, (11,11), 0)

        mask = cv2.inRange(hsv, LOWER_HSV, UPPER_HSV)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        ball_found = False

        if contours:
            c = max(contours, key=cv2.contourArea)

            if cv2.contourArea(c) > MIN_AREA:
                ball_found = True

                x, y, w, h = cv2.boundingRect(c)

                cx = x + w // 2
                cy = y + h // 2

                error = cx - FRAME_CENTER_X

                # DRAW BOX
                cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,255), 2)
                cv2.circle(frame, (cx,cy), 5, (0,0,255), -1)

                cv2.line(frame,
                         (FRAME_CENTER_X,0),
                         (FRAME_CENTER_X,480),
                         (255,255,255), 1)

                cv2.putText(frame,
                            f"Error: {error}",
                            (10,30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0,255,0),
                            2)

                # MOTOR CONTROL
                if abs(error) > DEADBAND:

                    set_direction(error > 0)

                    steps = min(20, max(1, abs(error)//15))

                    for _ in range(steps):
                        step()

        else:
            cv2.putText(frame,
                        "NO BALL",
                        (10,30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0,0,255),
                        2)

        cv2.imshow("Tracking", frame)
        cv2.imshow("Mask", mask)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    spi.close()
    DIR_PIN.close()
    STEP_PIN.close()
    CS_PIN.close()
