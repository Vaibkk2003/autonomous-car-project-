# Autonomous Car using MiDaS Depth Estimation and ESP8266

## Overview

This project implements a small autonomous car controlled through an **ESP8266 WiFi module** and **MiDaS depth estimation**.
The system uses a camera feed to estimate depth and navigate while avoiding obstacles.

The project also supports **manual remote control** and **environment mapping**.

---

## Project Files

* **esp8266 test.py**
  Used to test the connection between the computer and the ESP8266 module.

* **midas.py**
  Runs the autonomous driving system using **MiDaS depth estimation**.

* **midas_mapping.py**
  Used to generate a simple map of the surroundings.

* **remote_control.py**
  Allows manual control of the car.

* **Arduino Code (Word Document)**
  Contains the code that should be uploaded to the ESP8266 for motor control.

---

## How to Run

### 1. Test ESP8266 Connection

Run:

```
python esp8266 test.py
```

This checks whether the computer can communicate with the ESP8266.

---

### 2. Run Autonomous Car

Run:

```
python midas.py
```

The car will use **MiDaS depth estimation** to detect obstacles and move autonomously.

---

### 3. Run Mapping System

Run:

```
python midas_mapping.py
```

This script generates a simple map of the environment.

---

### 4. Manual Remote Control

Run:

```
python remote_control.py
```

This allows manual control of the car through keyboard commands.

---

## Technologies Used

* Python
* OpenCV
* PyTorch
* MiDaS Depth Estimation
* ESP8266 WiFi Module

---

## Author

Vaibhav K Kumbar
