#!/bin/bash
# Activate the arduino-serial conda environment and run the Python script
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

echo "Uploading sketch to $PORT..."
arduino-cli compile --fqbn arduino:avr:uno mq135.ino
if [ $? -ne 0 ]; then
  echo "Compilation failed!"
  exit 1
fi
arduino-cli upload -p "$PORT" --fqbn arduino:avr:uno mq135.ino
if [ $? -ne 0 ]; then
  echo "Upload failed!"
  exit 1
fi

echo "Waiting for Arduino to reboot..."
sleep 3

python /home/raspberrypi/Ulurover-Minilab/Ulurover-Minilab/Arduino-Serial-Connection/mq135/read-mq135-csv.py --seconds 10