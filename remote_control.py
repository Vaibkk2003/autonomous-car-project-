import socket
import cv2
import time

# ===================== ESP8266 CONNECTION =====================
ESP_IP = "192.168.31.196"
PORT = 9999

def connect_esp():
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((ESP_IP, PORT))
            print("Connected to ESP8266")
            return client
        except:
            print("Retrying ESP connection...")
            time.sleep(2)

client = connect_esp()

# ===================== CAMERA =====================
cap = cv2.VideoCapture("http://192.168.31.195:8080/video")

print("""
CONTROL YOUR CAR:
W - Forward
S - Stop
A - Left
D - Right
X - Backward
Q - Quit
""")

last_action = ""

# ===================== MAIN LOOP =====================
while True:
    ret, frame = cap.read()
    
    if ret:
        cv2.imshow("Camera", frame)

    key = cv2.waitKey(1) & 0xFF

    action = None

    if key == ord('w'):
        action = "F"
    elif key == ord('s'):
        action = "S"
    elif key == ord('a'):
        action = "L"
    elif key == ord('d'):
        action = "R"
    elif key == ord('x'):
        action = "B"
    elif key == ord('q'):
        break

    # Send command if key pressed
    if action:
        try:
            client.send((action + "\n").encode())
            
            if action != last_action:
                print("Action:", action)
                last_action = action

        except:
            print("Reconnecting ESP...")
            client = connect_esp()

# ===================== CLEANUP =====================
cap.release()
cv2.destroyAllWindows()
client.close()