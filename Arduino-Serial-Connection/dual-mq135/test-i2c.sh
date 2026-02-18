#!/bin/bash
# Test I2C Connection
# Upload I2C scanner to Arduino A to check if Arduino B is visible

source ~/miniconda3/etc/profile.d/conda.sh
conda activate arduino-serial

PORT=$(ls /dev/ttyACM* 2>/dev/null | head -n 1)
if [ -z "$PORT" ]; then
  PORT=$(ls /dev/ttyUSB* 2>/dev/null | head -n 1)
fi
if [ -z "$PORT" ]; then
  echo "No Arduino port found!"
  exit 1
fi

echo "=== I2C Scanner Test ==="
echo "Port: $PORT"
echo ""
echo "This will scan for I2C devices."
echo "Arduino B should appear at address 0x08"
echo ""

echo "Compiling I2C scanner..."
arduino-cli compile --fqbn arduino:avr:uno i2c_scanner
if [ $? -ne 0 ]; then
  echo "Compilation failed!"
  exit 1
fi

echo "Uploading to Arduino A..."
arduino-cli upload -p "$PORT" --fqbn arduino:avr:uno i2c_scanner
if [ $? -ne 0 ]; then
  echo "Upload failed!"
  exit 1
fi

echo ""
echo "Waiting for Arduino to reboot..."
sleep 2

echo ""
echo "Opening serial monitor (Ctrl+C to exit)..."
echo ""
python3 -c "
import serial
import time
ser = serial.Serial('$PORT', 9600, timeout=1)
time.sleep(1)
try:
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(line)
except KeyboardInterrupt:
    print('\n\nStopped.')
"
