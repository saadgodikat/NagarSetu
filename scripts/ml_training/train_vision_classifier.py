"""
Training Pipeline for NagarIQ Computer Vision Classifier (Phase 5).
Fine-tunes MobileNetV3-Small on 6 civic categories:
['garbage', 'pothole', 'drainage', 'streetlight', 'water_leakage', 'other'].
Saves versioned PyTorch checkpoint artifact to backend/models/complaint_vision_classifier_v1.pt.
"""

import os
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "vision_dataset"
MODEL_OUTPUT_PATH = BASE_DIR / "backend" / "models" / "complaint_vision_classifier_v1.pt"

CATEGORIES = [
    "garbage",
    "pothole",
    "drainage",
    "streetlight",
    "water_leakage",
    "other",
]


def train_model():
    print("============================================================")
    print("      NagarIQ MobileNetV3-Small Vision Training (Phase 5)   ")
    print("============================================================")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Training compute device: {device}")

    # Transforms
    data_transforms = {
        "train": transforms.Compose([
            transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]),
        "val": transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]),
        "test": transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]),
    }

    image_datasets = {
        x: datasets.ImageFolder(str(DATA_DIR / x), data_transforms[x])
        for x in ["train", "val", "test"]
    }

    dataloaders = {
        x: DataLoader(image_datasets[x], batch_size=32, shuffle=(x == "train"), num_workers=0)
        for x in ["train", "val", "test"]
    }

    class_names = image_datasets["train"].classes
    print(f"[*] Detected classes: {class_names}")

    # Load MobileNetV3-Small
    print("[*] Initializing MobileNetV3-Small backbone...")
    try:
        weights = models.MobileNet_V3_Small_Weights.DEFAULT
        model = models.mobilenet_v3_small(weights=weights)
    except Exception as e:
        print(f"[*] Note on weights: {e}, initializing clean architecture.")
        model = models.mobilenet_v3_small(weights=None)

    # Modify classification head
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, len(class_names))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=12)

    num_epochs = 12
    best_acc = 0.0
    best_weights = None

    print("\n[*] Starting Training Loop...")
    start_time = time.time()

    for epoch in range(1, num_epochs + 1):
        # Training Phase
        model.train()
        train_loss = 0.0
        train_correct = 0

        for inputs, labels in dataloaders["train"]:
            inputs = inputs.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            _, preds = torch.max(outputs, 1)

            loss.backward()
            optimizer.step()

            train_loss += loss.item() * inputs.size(0)
            train_correct += torch.sum(preds == labels.data).item()

        scheduler.step()
        train_acc = train_correct / len(image_datasets["train"])

        # Validation Phase
        model.eval()
        val_loss = 0.0
        val_correct = 0

        with torch.no_grad():
            for inputs, labels in dataloaders["val"]:
                inputs = inputs.to(device)
                labels = labels.to(device)

                outputs = model(inputs)
                loss = criterion(outputs, labels)
                _, preds = torch.max(outputs, 1)

                val_loss += loss.item() * inputs.size(0)
                val_correct += torch.sum(preds == labels.data).item()

        val_acc = val_correct / len(image_datasets["val"])
        print(f"  Epoch [{epoch:02d}/{num_epochs:02d}] - Train Acc: {train_acc*100:.1f}%, Val Acc: {val_acc*100:.1f}%")

        if val_acc >= best_acc:
            best_acc = val_acc
            best_weights = model.state_dict().copy()

    training_time = time.time() - start_time
    print(f"\n[+] Training completed in {training_time:.1f}s. Best Val Accuracy: {best_acc*100:.2f}%")

    # Load best weights
    model.load_state_dict(best_weights)

    # Save Model Artifact
    os.makedirs(MODEL_OUTPUT_PATH.parent, exist_ok=True)
    checkpoint = {
        "model_name": "mobilenet_v3_small",
        "num_classes": len(class_names),
        "classes": class_names,
        "state_dict": model.state_dict(),
        "best_val_acc": best_acc,
        "input_size": [3, 224, 224],
        "mean": [0.485, 0.456, 0.406],
        "std": [0.229, 0.224, 0.225],
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0.0",
    }
    torch.save(checkpoint, MODEL_OUTPUT_PATH)
    file_size_kb = MODEL_OUTPUT_PATH.stat().st_size / 1024
    print(f"[+] Model checkpoint saved: {MODEL_OUTPUT_PATH} ({file_size_kb:.1f} KB)")
    print("============================================================")


if __name__ == "__main__":
    train_model()
