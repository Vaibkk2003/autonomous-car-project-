import socket

ESP_IP = "192.168.31.196"   # change this
PORT = 9999

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((ESP_IP, PORT))

print("Connected to ESP8266")

while True:
    cmd = input("Enter command (F/B/L/R/S): ")
    client.send((cmd + "\n").encode())