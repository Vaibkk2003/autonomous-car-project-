import cv2
import socket
import time
import torch
import numpy as np

# ===================== ESP8266 CONNECTION =====================

ESP_IP = "192.168.29.128"
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

# ===================== LOAD MIDAS =====================

print("Loading MiDaS (FAST MODE)...")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
midas.to(device)
midas.eval()

use_half = device.type == "cuda"
if use_half:
    midas.half()

midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
transform = midas_transforms.small_transform

# ===================== CAMERA =====================

cap = cv2.VideoCapture("http://192.168.29.39:8080/video", cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# ===================== MAP SETTINGS =====================

MAP_SIZE = 500
grid = np.zeros((MAP_SIZE, MAP_SIZE))

robot_x = MAP_SIZE // 2
robot_y = MAP_SIZE // 2
robot_dir = 0   # 0=NORTH 1=EAST 2=SOUTH 3=WEST

last_action = ""
frame_count = 0
last_map_save = time.time()

TURN_THRESHOLD = 140
STOP_THRESHOLD = 200

# ===================== MAIN LOOP =====================

while True:

    ret, frame = cap.read()

    if not ret:
        print("Camera not working")
        break

    frame = cv2.resize(frame, (256, 192))
    frame_count += 1

    if frame_count % 4 != 0:
        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) == 27:
            break
        continue

    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    input_batch = transform(img_rgb).to(device)

    if use_half:
        input_batch = input_batch.half()

    # ===================== DEPTH =====================

    with torch.no_grad():
        prediction = midas(input_batch)

        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=img_rgb.shape[:2],
            mode="bilinear",
            align_corners=False
        ).squeeze()

    depth_map = prediction.cpu().numpy()

    depth_map = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX)
    depth_map = depth_map.astype(np.uint8)

    # ===================== ROI =====================

    h2, w2 = depth_map.shape
    roi_depth = depth_map[int(h2/2):h2, :]
    third = w2 // 3

    left_zone = roi_depth[:, :third]
    center_zone = roi_depth[:, third:2*third]
    right_zone = roi_depth[:, 2*third:]

    l_depth = np.mean(left_zone)
    c_depth = np.mean(center_zone)
    r_depth = np.mean(right_zone)

    action = "F"

    if c_depth > STOP_THRESHOLD:
        action = "S"

    elif c_depth > TURN_THRESHOLD:
        if l_depth < r_depth:
            action = "L"
        else:
            action = "R"

    # ===================== ROBOT POSITION UPDATE =====================

    if action == "F":

        if robot_dir == 0:
            robot_y -= 1
        elif robot_dir == 1:
            robot_x += 1
        elif robot_dir == 2:
            robot_y += 1
        elif robot_dir == 3:
            robot_x -= 1

    elif action == "L":
        robot_dir = (robot_dir - 1) % 4

    elif action == "R":
        robot_dir = (robot_dir + 1) % 4

    # keep robot inside map

    robot_x = max(2, min(MAP_SIZE - 3, robot_x))
    robot_y = max(2, min(MAP_SIZE - 3, robot_y))

    # ===================== MAP UPDATE =====================

    obstacle_distance = int(c_depth / 30)
    obstacle_distance = min(10, obstacle_distance)

    if robot_dir == 0:
        ox = robot_x
        oy = robot_y - obstacle_distance

    elif robot_dir == 1:
        ox = robot_x + obstacle_distance
        oy = robot_y

    elif robot_dir == 2:
        ox = robot_x
        oy = robot_y + obstacle_distance

    else:
        ox = robot_x - obstacle_distance
        oy = robot_y

    if 0 <= ox < MAP_SIZE and 0 <= oy < MAP_SIZE:
        grid[ox][oy] = 1

    # ===================== SEND COMMAND =====================

    try:
        speed = 250
        client.send(f"{action},{speed}\n".encode())

        if action != last_action:
            print(f"Action: {action} | L:{l_depth:.0f} C:{c_depth:.0f} R:{r_depth:.0f}")
            last_action = action

    except:
        print("Reconnecting ESP...")
        client = connect_esp()

    # ===================== DISPLAY =====================

    depth_color = cv2.applyColorMap(depth_map, cv2.COLORMAP_INFERNO)

    half_h = int(h2/2)
    cv2.line(depth_color, (third, half_h), (third, h2), (255,255,255), 2)
    cv2.line(depth_color, (2*third, half_h), (2*third, h2), (255,255,255), 2)
    cv2.line(depth_color, (0, half_h), (w2, half_h), (255,255,255), 2)

    # ===================== DRAW MAP =====================

    map_img = np.zeros((MAP_SIZE, MAP_SIZE, 3), dtype=np.uint8)
    map_img[grid == 1] = (255,255,255)

    if 0 <= robot_x < MAP_SIZE and 0 <= robot_y < MAP_SIZE:
        map_img[robot_x, robot_y] = (0,0,255)

    map_display = cv2.resize(map_img, (600,600), interpolation=cv2.INTER_NEAREST)

    cv2.putText(frame, f"ACTION: {action}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

    cv2.imshow("Camera", frame)
    cv2.imshow("Depth", depth_color)
    cv2.imshow("House Map", map_display)

    # save map every 10 seconds

    if time.time() - last_map_save > 10:
        cv2.imwrite("house_map_live.png", map_img)
        last_map_save = time.time()

    if cv2.waitKey(1) == 27:
        break


# ===================== SAVE FINAL MAP =====================

cv2.imwrite("house_map_final.png", map_img)

# ===================== CLEANUP =====================

cap.release()
cv2.destroyAllWindows()
client.close()