import cv2, numpy as np
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # Click a pixel on the ball to print its HSV value
    def pick(event, x, y, *_):
        if event == cv2.EVENT_LBUTTONDOWN:
            print("HSV:", hsv[y, x])
    cv2.imshow("pick", frame)
    cv2.setMouseCallback("pick", pick)
    if cv2.waitKey(1) == 27: break
cap.release(); cv2.destroyAllWindows()
