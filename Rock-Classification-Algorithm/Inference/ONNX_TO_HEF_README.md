# ONNX to HEF Conversion Guide

## Overview
This guide documents the process of converting an EfficientNet-B0 PyTorch model to Hailo HEF format for deployment on Hailo-8L AI accelerator hardware.

## Prerequisites

### Hardware Requirements
- Target: Hailo-8L AI accelerator
- Development: x86_64 Linux system with 8GB+ RAM

### Software Requirements
- Miniconda3 or Anaconda
- Hailo Dataflow Compiler 3.33.0
- Python 3.10

## Setup

### 1. Create Conda Environment
```bash
conda create -n hailodfc python=3.10 -y
conda activate hailodfc
```

### 2. Install Hailo Dataflow Compiler

Download the Hailo Dataflow Compiler wheel file from [Hailo Developer Zone](https://hailo.ai/developer-zone/) and install:

```bash
# If downloaded to ~/Downloads
pip install ~/Downloads/hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl

# Or specify the full path
pip install /path/to/hailo_dataflow_compiler-3.33.0-py3-none-linux_x86_64.whl
```

### 3. Install Hailo Model Zoo (Optional but Recommended)
```bash
pip install hailo-model-zoo
```

**Note:** After installation, you can safely delete the `.whl` file from your Downloads folder to free up space.

## Files Overview

### Input Files
- `rock_classifier_efficientnet_b0.pth` - Trained PyTorch model weights
- `classes.json` - Rock classification labels (18 classes)
- Calibration images - Representative dataset for quantization (6 images per class recommended)

### Generated Files
- `rock_classifier_efficientnet_b0_opset11.onnx` - ONNX model with opset 11 (16 MB)
- `calibration_npy/` - Preprocessed calibration data in numpy format (94+ files)
- `efficientnet_b0_rock_classifier.hef` - Final Hailo Executable Format file (12-13 MB)

### Scripts
- `export_onnx_opset11.py` - Export PyTorch model to ONNX opset 11
- `prepare_calibration_npy.py` - Convert calibration images to numpy arrays
- `compile_rock_classifier.py` - Main compilation script

## Conversion Process

### Step 1: Export ONNX Model (Opset 11)

**Why Opset 11?** Hailo DFC 3.33.0 requires ONNX opset version 11. Modern PyTorch exports opset 18+ by default.

```bash
# Option A: If you have PyTorch 1.13.x installed
python export_onnx_opset11.py

# Option B: Create temporary environment with older PyTorch
conda create -n pytorch113 python=3.9 -y
conda activate pytorch113
pip install torch==1.13.1 torchvision==0.14.1 onnx
python export_onnx_opset11.py
conda deactivate
conda remove -n pytorch113 --all -y
conda activate hailodfc
```

**Output:** `rock_classifier_efficientnet_b0_opset11.onnx` (15.4 MB)

### Step 2: Prepare Calibration Data

Calibration data is used for quantization (converting float32 → int8) while maintaining accuracy.

**Requirements:**
- Minimum: 64 images
- Recommended: 100+ images (6 per class × 18 classes = 108)
- Must be representative of real-world data

```bash
# Place calibration images in calibration_data/ directory
# Structure: calibration_data/*.jpg

# Convert to numpy format (required by Hailo DFC 3.33.0)
python prepare_calibration_npy.py
```

**What it does:**
- Resizes images to 224×224 (EfficientNet-B0 input size)
- Normalizes using ImageNet mean/std
- Converts to NCHW format (batch, channels, height, width)
- Saves as `.npy` files

**Output:** `calibration_npy/` directory with 94+ numpy arrays

### Step 3: Compile to HEF

**Important:** Make sure the `hailodfc` conda environment is activated before running:

```bash
conda activate hailodfc
python3 compile_rock_classifier.py
```

**What happens:**
1. **Translation** (2-3 seconds): ONNX → Hailo IR
2. **Optimization** (1-3 minutes): Applies quantization using calibration data
3. **Compilation** (45-55 minutes): Generates optimal partition across Hailo-8L contexts

**Compilation Process:**
- Tests different context partitions (4 → 5 → 6 contexts)
- Each iteration optimizes performance
- Allocates model layers to Hailo-8L clusters
- Generates final HEF binary

**Output:** `efficientnet_b0_rock_classifier.hef` (12-13 MB)

### Expected Compilation Messages

```
✓ Found 94 calibration arrays
[1/4] Initializing Hailo SDK Client...
[2/4] Loading ONNX model...
[info] Translation completed on ONNX model efficientnet_b0_rock_classifier (completion time: 00:00:03.11)
[3/4] Optimizing model for Hailo-8L...
      Using 94 calibration samples from calibration_npy
[info] Starting Model Optimization
[info] Using dataset with 64 entries for calibration
Calibration: 100%|████████████████████████████████| 64/64 [01:47<00:00,  1.59s/entries]
[info] Model Optimization is done
✓ Optimization complete
[4/4] Compiling to HEF format...
[info] Finding the best partition to contexts...
Found valid partition to 4 contexts
[info] Searching for a better partition...
Found valid partition to 5 contexts, Performance improved by 6.1%
[info] Searching for a better partition...
Found valid partition to 6 contexts, Performance improved by 2.9%
[info] Partition to contexts finished successfully
[info] Partitioner finished after 246 iterations, Time it took: 44m 51s
[info] Successful Mapping (allocation time: 47m 14s)
[info] Building HEF...
[info] Successful Compilation (compilation time: 30s)

==================================================
✓ Compilation completed successfully!
✓ Output: efficientnet_b0_rock_classifier.hef
✓ File size: 12.05 MB
==================================================
```

**Total time:** ~50-55 minutes on typical development machine

## Important Notes

### Calibration Data Requirements
- **Format:** Must be numpy arrays (`.npy`) for DFC 3.33.0
- **Preprocessing:** Must match model's training preprocessing
- **Quantity:** More data = better quantization (diminishing returns after 1024)

### ONNX Opset Compatibility
| Hailo DFC Version | ONNX Opset | PyTorch Version |
|-------------------|------------|-----------------|
| 3.33.0            | 11         | 1.13.x or older |
| 5.1.0+            | 17         | 2.0.x or newer  |

### Optimization Warnings
You may see these warnings (they're normal):
- `Reducing optimization level to 0` - Due to limited calibration data (<1024 images)
- `No GPU found, falling back to CPU` - Compilation works fine on CPU
- `Calibration set not normalized` - Some normalization happens on CPU at runtime

### Performance Optimization
The compiler searches for optimal partitioning across Hailo contexts:
- Starts with 4 contexts, may increase to 5 or 6
- Each iteration tests different layer distributions across hardware clusters
- Stops when improvements plateau (typically after 200-250 iterations)
- Final partition: 6 contexts for EfficientNet-B0
- Resource utilization: ~60% control, ~20-35% compute, ~25-30% memory per context
- Total optimization time: 45-55 minutes

## Troubleshooting

### Error: ONNX opset version not supported
**Solution:** Use `export_onnx_opset11.py` with PyTorch 1.13.x

### Error: StopIteration in npy_dir_to_dataset
**Solution:** Calibration data must be `.npy` files, not `.jpg`
Run `prepare_calibration_npy.py`

### Error: Model architecture mismatch
**Solution:** Ensure ONNX export uses same architecture as trained model
(torchvision vs lukemelas implementations have different layer names)

### Warning: Less than 1024 calibration samples
**Impact:** Quantization may be suboptimal, accuracy might decrease 5-10%
**Solution:** Collect more representative images if accuracy is critical

### Compilation takes very long (>60 minutes)
**Typical time:** 45-55 minutes for EfficientNet-B0

**Causes for longer compilation:**
- Complex model architecture with many layers
- Limited system resources (use dedicated machine with 8GB+ RAM)
- Many calibration samples (>1000)
- CPU-only compilation (no GPU acceleration)

**Normal behavior:** The compiler spends most time on:
- Context partitioning (40-45 minutes)
- Resource allocation/mapping (45-50 minutes)
- Final compilation and HEF building (<1 minute)

## Deployment

Once you have theRaspberry Pi with Hailo AI Kit:**
   ```bash
   scp efficientnet_b0_rock_classifier.hef pi@raspberrypi.local:/home/pi
   ```bash
   scp rock_classifier_efficientnet_b0.hef user@hailo-device:/path/to/models/
   ```

2. **Use Hailo Runtime API** to load and run inference:
   ```python
   from hailo_platform import HailoRT
   # Load HEF and run inference
   ```

3. **Test performance:**
   - Measure FPS (frames per second)
   - Verify accuracy on validation set
   - Compare to PyTorch baseline

## Expected Performance

- **Quantization:** float32 → int8 (4× smaller, faster)
- **Accuracy loss:** Typically <2% with good calibration (94 samples used)
- **Inference speed:** ~100-200 FPS on Hailo-8L (depends on preprocessing)
- **Model size:** 12.05 MB HEF vs 16 MB ONNX
- **Hardware:** Optimized for Hailo-8L with 6-context partition

## Rock Classification Classes

The model classifies 18 rock types:
```json
["Basalt", "Chert", "Clay", "Coal", "Conglomerate", "Diatomite", 
 "Dolomite", "Granite", "Gypsum", "Limestone", "Marble", "Obsidian", 
 "Quartzite", "Sandstone", "Shale", "Siliceous-sinter", "Slate", 
 "olivine-basalt"]
```

## References

- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [Hailo Dataflow Compiler Documentation](https://hailo.ai/developer-zone/documentation/dataflow-compiler/)
- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)
- [ONNX Documentation](https://onnx.ai/)

## Version History

- **v1.0** - Initial working compilation process for Hailo-8L
- **Target:** Hailo DFC 3.33.0, ONNX opset 11
- **Date:** December 2025
