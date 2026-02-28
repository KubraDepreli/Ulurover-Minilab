import numpy as np
from PIL import Image
import json
from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams,
                            InputVStreamParams, OutputVStreamParams, FormatType)

# Load class names
with open("./classes.json", "r") as f:
    rock_classes = json.load(f)

# Load and configure the HEF file
hef_path = "./ONNX-HEF-Conversion/efficientnet_b0_rock_classifier.hef"
hef = HEF(hef_path)

# Create VDevice
target = VDevice()

# Configure the device
configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
network_group = target.configure(hef, configure_params)[0]
network_group_params = network_group.create_params()

# Get input and output information
input_vstreams_params = InputVStreamParams.make(network_group, quantized=False, format_type=FormatType.FLOAT32)
output_vstreams_params = OutputVStreamParams.make(network_group, quantized=False, format_type=FormatType.FLOAT32)

# Get input shape from HEF
input_vstream_info = network_group.get_input_vstream_infos()[0]
input_shape = input_vstream_info.shape
print(f"Expected input shape: {input_shape}")

# Load and preprocess image
image_path = "../../Images/Test-Rocks/hematite-haematite-mineral-stone-isolated-photo.jpg"
image = Image.open(image_path).convert("RGB")

# Resize to match HEF expected input (height, width from shape)
expected_height, expected_width = input_shape[0], input_shape[1]
image = image.resize((expected_width, expected_height))

# Convert to numpy and normalize
img_array = np.array(image).astype(np.float32) / 255.0
mean = np.array([0.485, 0.456, 0.406])
std = np.array([0.229, 0.224, 0.225])
img_array = (img_array - mean) / std

# Ensure HWC format (Hailo expects NHWC)
if img_array.shape[-1] != 3:
    img_array = np.transpose(img_array, (1, 2, 0))

# Create input dictionary
input_data = {input_vstream_info.name: np.expand_dims(img_array, axis=0).astype(np.float32)}

# Run inference
with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
    with network_group.activate(network_group_params):
        output = infer_pipeline.infer(input_data)

# Process output
output_name = list(output.keys())[0]
predictions = output[output_name][0]

# Get predicted class
predicted_class = np.argmax(predictions)
probabilities = np.exp(predictions) / np.sum(np.exp(predictions))  # Softmax

print(f"Predicted rock type: {rock_classes[predicted_class]}")
print(f"Confidence: {probabilities[predicted_class]:.2%}")
print(f"\nTop 3 predictions:")
top3_indices = np.argsort(probabilities)[-3:][::-1]
for idx in top3_indices:
    print(f"  {rock_classes[idx]}: {probabilities[idx]:.2%}")
