import serial
import time
import glob

# Find all Arduino Nano serial ports (usually ttyUSB* or ttyACM*)
def find_arduino_ports():
    ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    return ports

# Connect to all found Arduinos
arduino_ports = find_arduino_ports()
if len(arduino_ports) < 2:
    print("Error: Less than two Arduino Nanos detected.")
    exit(1)

arduinos = []
for port in arduino_ports[:2]:
    try:
        ser = serial.Serial(port, 9600, timeout=2)
        arduinos.append(ser)
        print(f"Connected to Arduino on {port}")
    except Exception as e:
        print(f"Failed to connect to {port}: {e}")

# Function to set blink rate on both Arduinos
def set_blink_rate(rate):
    for ser in arduinos:
        ser.write(f"{rate}\n".encode())
        print(f"Sent blink rate {rate} to {ser.port}")

if __name__ == "__main__":
    while True:
        try:
            rate = input("Enter blink rate in ms (or 'exit'): ")
            if rate.lower() == 'exit':
                break
            if not rate.isdigit():
                print("Please enter a valid number.")
                continue
            set_blink_rate(rate)
        except KeyboardInterrupt:
            break
    for ser in arduinos:
        ser.close()
    print("Disconnected from Arduinos.")
