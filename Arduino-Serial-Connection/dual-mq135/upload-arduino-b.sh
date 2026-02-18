#!/bin/bash
# Upload Arduino B (Slave) Sketch
# Run this script BEFORE connecting Arduino B via I2C to Arduino A
#
# Connect Arduino B to USB, run this script, then disconnect and 
# connect Arduino B to Arduino A via I2C

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

echo "=== Arduino B (Slave) Upload ==="
echo "Port: $PORT"
echo ""

echo "Compiling arduino_b_slave.ino..."
arduino-cli compile --fqbn arduino:avr:uno arduino_b_slave
if [ $? -ne 0 ]; then
  echo "Compilation failed!"
  exit 1
fi

echo "Uploading to Arduino B..."
arduino-cli upload -p "$PORT" --fqbn arduino:avr:uno arduino_b_slave
if [ $? -ne 0 ]; then
  echo "Upload failed!"
  exit 1
fi

echo ""
echo "SUCCESS! Arduino B is now programmed as I2C slave."
echo ""
echo "Next steps:"
echo "1. Disconnect Arduino B from USB"
echo "2. Connect Arduino B to Arduino A via I2C:"
echo "   - SDA: A4 to A4"
echo "   - SCL: A5 to A5"
echo "   - GND: GND to GND"
echo "3. Power Arduino B (if needed)"
echo "4. Run ./run-dual-mq135.sh"
