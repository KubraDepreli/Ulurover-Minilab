#!/usr/bin/env python3
"""
Export PyTorch model to ONNX opset 11 for Hailo DFC 3.33.0 compatibility.
Uses PyTorch 1.13.x which properly supports opset 11.
"""

import torch
import torch.nn as nn
from torchvision.models import efficientnet_b0

def export_for_hailo_dfc_3():
    print("="*70)
    print("Exporting EfficientNet-B0 to ONNX Opset 11 for Hailo DFC 3.33.0")
    print("="*70)
    
    # Load model
    model_path = "../rock_classifier_efficientnet_b0.pth"
    print(f"\n[1/4] Loading model: {model_path}")
    
    # Create model architecture
    model = efficientnet_b0(pretrained=False)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 18)
    
    # Load weights
    checkpoint = torch.load(model_path, map_location='cpu')
    if isinstance(checkpoint, dict):
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        elif 'state_dict' in checkpoint:
            model.load_state_dict(checkpoint['state_dict'])
        else:
            model.load_state_dict(checkpoint)
    else:
        model.load_state_dict(checkpoint)
    
    model.eval()
    print("✓ Model loaded")
    
    # Dummy input - MUST match training resolution
    dummy_input = torch.randn(1, 3, 260, 260)
    output_path = "rock_classifier_efficientnet_b0_opset11.onnx"
    
    print(f"\n[2/4] Exporting to ONNX...")
    print(f"  Target: {output_path}")
    print(f"  Input size: 260x260 (matches training)")
    print(f"  Opset: 11 (Hailo DFC 3.33.0 compatible)")
    
    # Export with opset 11
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=11,  # Critical for Hailo DFC 3.33.0
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes=None,  # Keep it simple for Hailo
        verbose=False
    )
    
    print("✓ ONNX export complete")
    
    # Verify
    print(f"\n[3/4] Verifying ONNX model...")
    import onnx
    onnx_model = onnx.load(output_path)
    onnx.checker.check_model(onnx_model)
    print("✓ Model is valid")
    
    # Info
    print(f"\n[4/4] Model Information:")
    print(f"  Input: {onnx_model.graph.input[0].name}")
    print(f"  Output: {onnx_model.graph.output[0].name}")
    print(f"  Opset: {onnx_model.opset_import[0].version}")
    print(f"  Size: {len(open(output_path, 'rb').read()) / 1024 / 1024:.1f} MB")
    
    print("\n" + "="*70)
    print("✓ SUCCESS! Ready for Hailo compilation")
    print("="*70)
    print(f"\nNext: python compile_rock_classifier.py")
    
    return output_path

if __name__ == "__main__":
    try:
        export_for_hailo_dfc_3()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
