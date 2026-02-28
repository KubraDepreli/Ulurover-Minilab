import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
from torchvision.models import efficientnet_b0
import json

class RockClassifier(nn.Module):
    def __init__(self, num_classes=18, dropout=0.3):
        super().__init__()
        base = efficientnet_b0(weights=None)
        self.features = base.features
        in_features = base.classifier[1].in_features
        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout, inplace=True),
            nn.Linear(in_features, num_classes)
        )
        self.attention_pool = nn.AdaptiveAvgPool2d(1)

    def forward(self, x):
        x = self.features(x)
        x = self.attention_pool(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)

model = RockClassifier()
model.load_state_dict(torch.load("./rock_classifier_efficientnet_b0.pth", map_location=torch.device('cpu'), weights_only=False))
model.eval()

with open("./classes.json", "r") as f:
    rock_classes = json.load(f)

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

image_path = "../../Images/Test-Rocks/hematite-haematite-mineral-stone-isolated-photo.jpg"
image = Image.open(image_path).convert("RGB")
input_tensor = transform(image).unsqueeze(0)

with torch.no_grad():
    output = model(input_tensor)

predicted_class = torch.argmax(output, dim=1).item()
probabilities = torch.softmax(output, dim=1).squeeze()

print("PyTorch Model Results (260x260):")
print(f"Predicted rock type: {rock_classes[predicted_class]}")
print(f"Confidence: {probabilities[predicted_class].item():.2%}")
print(f"\nTop 3 predictions:")
top3_probs, top3_indices = torch.topk(probabilities, 3)
for prob, idx in zip(top3_probs, top3_indices):
    print(f"  {rock_classes[idx]}: {prob.item():.2%}")
