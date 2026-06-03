from picamera2 import Picamera2
import cv2

picam2 = Picamera2()
picam2.start()

current_hsv = None

def pick(event, x, y, flags, param):
    global current_hsv

    if event == cv2.EVENT_LBUTTONDOWN and current_hsv is not None:
        print("HSV:", current_hsv[y, x])

cv2.namedWindow("pick")
cv2.setMouseCallback("pick", pick)

while True:
    frame = picam2.capture_array()

    # Uncomment if colors seem wrong
    # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    current_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    cv2.imshow("pick", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cv2.destroyAllWindows()
