#!/usr/bin/env python3
"""
Convert ONNX model to HEF format using Hailo Dataflow Compiler
For Raspberry Pi AI Kit (Hailo-8L)
"""

from hailo_sdk_client import ClientRunner

# Initialize ClientRunner for Hailo-8L
runner = ClientRunner(hw_arch='hailo8l')

# File paths
onnx_model = 'rock_classifier_efficientnet_b0_opset11.onnx'
hef_output = 'rock_classifier_efficientnet_b0.hef'

print(f"Converting {onnx_model} to HEF format...")
print(f"Target hardware: Hailo-8L (Raspberry Pi AI Kit)")
print("-" * 60)

# Step 1: Parse ONNX model
print("\n[1/3] Parsing ONNX model...")
hn, npz = runner.translate_onnx_model(
    onnx_model,
    net_name='rock_classifier'
)
print("✓ Model parsed successfully")

# Step 2: Optimize model
print("\n[2/3] Optimizing model for Hailo hardware...")
runner.optimize(hn)
print("✓ Model optimized")

# Step 3: Compile to HEF
print("\n[3/3] Compiling to HEF...")
hef = runner.compile(hn, hef_output)
print(f"✓ HEF file created: {hef_output}")

print("\n" + "=" * 60)
print(f"SUCCESS! Your model is ready: {hef_output}")
print("=" * 60)
