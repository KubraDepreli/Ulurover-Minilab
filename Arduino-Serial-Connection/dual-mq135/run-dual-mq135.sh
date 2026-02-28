#!/bin/bash
# Dual MQ-135 Protocol Runner
# Uploads Arduino A sketch and runs Python script to collect data
#
# NOTE: Arduino B (slave) must be uploaded separately first!
# Upload arduino_b_slave.ino to the secondary Arduino before running this script.

source ~/miniconda3/etc/profile.d/conda.sh
conda activate arduino-serial

# Auto-detect Arduino port
PORT=$(ls /dev/ttyACM* 2>/dev/null | head -n 1)
if [ -z "$PORT" ]; then
  PORT=$(ls /dev/ttyUSB* 2>/dev/null | head -n 1)
fi
if [ -z "$PORT" ]; then
  echo "No Arduino port found!"
  exit 1
fi

echo "=== Dual MQ-135 Protocol ==="
echo "Arduino A (Master): Connected to USB at $PORT"
echo "Arduino B (Slave): Connected via I2C at address 0x08"
echo ""

echo "Uploading sketch to Arduino A at $PORT..."
arduino-cli compile --fqbn arduino:avr:uno arduino_a_master
if [ $? -ne 0 ]; then
  echo "Compilation failed!"
  exit 1
fi
arduino-cli upload -p "$PORT" --fqbn arduino:avr:uno arduino_a_master
if [ $? -ne 0 ]; then
  echo "Upload failed!"
  exit 1
fi

echo "Waiting for Arduino A to reboot..."
sleep 3

echo ""
echo "Starting data collection..."
python /home/raspberrypi/Ulurover-Minilab/Ulurover-Minilab/Arduino-Serial-Connection/dual-mq135/read-dual-mq135-csv.py --seconds 10
