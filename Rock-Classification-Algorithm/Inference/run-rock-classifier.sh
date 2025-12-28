#!/bin/bash
# Wrapper script to run rock classifier with conda environment

# Initialize conda
source ~/miniconda3/etc/profile.d/conda.sh

# Activate the environment
conda activate rock-classification

# Run the classifier
cd /home/raspberrypi/Rock-Classifier/Ulurover-Minilab/Rock-Classification-Algorithm/Inference
python rock-classifier-plain.py "$@"
