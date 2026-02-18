
#!/bin/bash
# Activate the arduino-serial conda environment and run the Python script
source ~/miniconda3/etc/profile.d/conda.sh
conda activate arduino-serial
python ~/Arduino-Serial-Connection/arduino_dual_blink.py
