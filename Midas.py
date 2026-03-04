import cv2
import socket
import time
import torch
import numpy as np

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

# ===================== LOAD MIDAS =====================
print("Loading MiDaS (FAST MODE)...")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
midas.to(device)
midas.eval()

# 🔥 Use FP16 if GPU available
use_half = device.type == "cuda"
if use_half:
    midas.half()

# Transforms
midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
transform = midas_transforms.small_transform

# ===================== CAMERA =====================
cap = cv2.VideoCapture("http://192.168.31.195:8080/video", cv2.CAP_FFMPEG)

# 🔥 Reduce internal buffer (less delay)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# ===================== SETTINGS =====================
last_action = ""
frame_count = 0

TURN_THRESHOLD = 140
STOP_THRESHOLD = 200

# ===================== MAIN LOOP =====================
while True:
    ret, frame = cap.read()

    if not ret:
        print("Camera not working")
        break

    # 🔥 Resize (BIG SPEED BOOST)
    frame = cv2.resize(frame, (256, 192))

    frame_count += 1

    # 🔥 Skip frames (VERY IMPORTANT)
    if frame_count % 4 != 0:
        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) == 27:
            break
        continue

    # ===================== AI INPUT =====================
    # FIX 1: Feed the WHOLE frame to the AI so it understands context
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    input_batch = transform(img_rgb).to(device)

    if use_half:
        input_batch = input_batch.half()

    # ===================== DEPTH =====================
    with torch.no_grad():
        prediction = midas(input_batch)

        # 🔥 Faster interpolation
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=img_rgb.shape[:2],
            mode="bilinear",   # faster than bicubic
            align_corners=False,
        ).squeeze()

    depth_map = prediction.cpu().numpy()

    # 🔥 Fast normalization
    depth_map = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX)
    depth_map = depth_map.astype(np.uint8)

    # ===================== ROI & DECISION =====================
    h2, w2 = depth_map.shape
    
    # FIX 2: Crop the depth map AFTER the AI processes it
    roi_depth = depth_map[int(h2/2):h2, :] 
    third = w2 // 3

    # Analyze the bottom ROI only
    left_zone = roi_depth[:, :third]
    center_zone = roi_depth[:, third:2*third]
    right_zone = roi_depth[:, 2*third:]

    l_depth = np.mean(left_zone)
    c_depth = np.mean(center_zone)
    r_depth = np.mean(right_zone)

    action = "F"

    # STOP
    if c_depth > STOP_THRESHOLD:
        action = "S"

    # TURN
    elif c_depth > TURN_THRESHOLD:
        if l_depth < r_depth:
            action = "L"
        else:
            action = "R"

    # ===================== SEND COMMAND =====================
    # FIX 3: Send the command EVERY frame to keep the ESP8266 timer alive
    try:
        client.send((action + "\n").encode())
        
        # Only print to the terminal if the action CHANGES
        if action != last_action:
            print(f"Action: {action} | L:{l_depth:.0f} C:{c_depth:.0f} R:{r_depth:.0f}")
            last_action = action

    except:
        print("Reconnecting ESP...")
        client = connect_esp()

    # ===================== DISPLAY =====================
    depth_color = cv2.applyColorMap(depth_map, cv2.COLORMAP_INFERNO)

    # Draw guides on the bottom half of the depth map to show our ROI
    half_h = int(h2/2)
    cv2.line(depth_color, (third, half_h), (third, h2), (255,255,255), 2)
    cv2.line(depth_color, (2*third, half_h), (2*third, h2), (255,255,255), 2)
    cv2.line(depth_color, (0, half_h), (w2, half_h), (255,255,255), 2)

    cv2.putText(frame, f"ACTION: {action}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

    cv2.imshow("Camera", frame)
    cv2.imshow("Depth", depth_color)

    if cv2.waitKey(1) == 27:
        break

# ===================== CLEANUP =====================
cap.release()
cv2.destroyAllWindows()
client.close()