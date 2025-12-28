#!/usr/bin/env python3
"""
Compile EfficientNet-B0 Rock Classifier to Hailo HEF format
"""
import os
import sys

# Check if calibration data exists (prefer numpy format)
calib_dir = 'calibration_npy'
if os.path.exists(calib_dir):
    num_images = len([f for f in os.listdir(calib_dir) 
                      if f.endswith('.npy')])
    print(f"✓ Found {num_images} calibration arrays")
else:
    calib_dir = 'calibration_data'
    if os.path.exists(calib_dir):
        num_images = len([f for f in os.listdir(calib_dir) 
                          if f.endswith(('.jpg', '.jpeg', '.png'))])
        print(f"✓ Found {num_images} calibration images")
    else:
        print("⚠️  No calibration data found - using random calibration")
        num_images = 0

try:
    from hailo_sdk_client import ClientRunner
    
    print("\n" + "="*50)
    print("Hailo Rock Classifier Compilation")
    print("="*50)
    
    # Model configuration - prefer opset 11 version
    onnx_model = 'rock_classifier_efficientnet_b0_opset11.onnx'
    model_name = 'efficientnet_b0_rock_classifier'
    hw_arch = 'hailo8l'
    
    # Fallback chain
    if not os.path.exists(onnx_model):
        onnx_model = 'rock_classifier_efficientnet_b0_simplified.onnx'
        print("⚠️  Using simplified model (opset 18 - may not work)")
    
    if not os.path.exists(onnx_model):
        onnx_model = 'rock_classifier_efficientnet_b0.onnx'
        print("⚠️  Using original ONNX - run: python export_onnx_opset11.py")
    
    if not os.path.exists(onnx_model):
        print(f"Error: ONNX model not found: {onnx_model}")
        sys.exit(1)
    
    print(f"\nModel: {onnx_model}")
    print(f"Hardware: {hw_arch}")
    print(f"Target: HEF format\n")
    
    # Create Hailo runner
    print("[1/4] Initializing Hailo SDK Client...")
    runner = ClientRunner(hw_arch=hw_arch)
    
    # Load ONNX model
    print(f"[2/4] Loading ONNX model...")
    runner.translate_onnx_model(
        onnx_model,
        model_name,
        start_node_names=None,
        end_node_names=None
    )
    
    # Optimize model with calibration data
    print("[3/4] Optimizing model for Hailo-8L...")
    try:
        # For DFC 3.33.0, pass calibration path and type to optimize
        from hailo_sdk_client.exposed_definitions import CalibrationDataType
        
        if num_images > 0:
            print(f"      Using {num_images} calibration samples from {calib_dir}")
            runner.optimize(calib_dir, data_type=CalibrationDataType.npy_dir)
        else:
            print("      Using random calibration (may reduce accuracy)")
            runner.optimize(None, data_type=CalibrationDataType.auto)
        
        print("✓ Optimization complete")
    except Exception as e:
        print(f"❌ Optimization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Compile to HEF (quantization already happened during optimize)
    print("[4/4] Compiling to HEF format...")
    hef_path = runner.compile()
    
    print("\n" + "="*50)
    print("✓ Compilation completed successfully!")
    print(f"✓ Output: {hef_path}")
    print("="*50)
    print("\nNext steps:")
    print("  1. Transfer the .hef file to your Hailo device")
    print("  2. Use Hailo Runtime API to run inference")
    print("  3. Test model performance\n")
    
except ImportError as e:
    print(f"\nError: Hailo SDK not properly installed")
    print(f"Details: {e}")
    print("\nMake sure you're in the hailodfc conda environment:")
    print("  conda activate hailodfc")
    sys.exit(1)
except Exception as e:
    print(f"\nError during compilation: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
