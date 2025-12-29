#!/usr/bin/env python3
"""
Convert JPG calibration images to numpy arrays for Hailo DFC
"""
import os
import numpy as np
from PIL import Image
from pathlib import Path

# Configuration
calib_dir = Path("../calibration_data")
output_dir = Path("calibration_npy")
input_size = 224  # EfficientNet-B0 input size

# ImageNet normalization (standard for EfficientNet)
mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)

print(f"Converting calibration images from {calib_dir} to {output_dir}")

# Create output directory
output_dir.mkdir(exist_ok=True)

# Get all image files
image_files = list(calib_dir.glob("*.jpg")) + list(calib_dir.glob("*.jpeg"))
print(f"Found {len(image_files)} images")

# Convert each image
for idx, img_path in enumerate(image_files, 1):
    # Load image
    img = Image.open(img_path).convert('RGB')
    
    # Resize to model input size
    img = img.resize((input_size, input_size), Image.BILINEAR)
    
    # Convert to numpy array [H, W, C] in range [0, 255]
    img_array = np.array(img, dtype=np.float32)
    
    # Normalize to [0, 1]
    img_array = img_array / 255.0
    
    # Apply ImageNet normalization
    img_array = (img_array - mean) / std
    
    # IMPORTANT: Hailo expects HWC format (height, width, channels)
    # Keep as (224, 224, 3) - do NOT transpose to NCHW
    
    # Save as numpy file
    output_path = output_dir / f"{img_path.stem}.npy"
    np.save(output_path, img_array)
    
    if idx % 10 == 0:
        print(f"  Processed {idx}/{len(image_files)} images...")

print(f"\n✓ Successfully converted {len(image_files)} images")
print(f"  Output directory: {output_dir}")
print(f"  Array shape: ({input_size}, {input_size}, 3) [HWC format]")
print(f"  Data type: float32")
print(f"  Normalized: ImageNet mean/std")
