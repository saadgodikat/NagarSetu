"""
Prepares a balanced, multi-class visual dataset for NagarIQ Computer Vision training.
Supports 6 classes: garbage, pothole, drainage, streetlight, water_leakage, other.
Generates structured visual samples with representative feature textures, shapes, and noise augmentations.
"""

import math
import os
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_IMAGE_DIR = BASE_DIR / "data" / "vision_dataset"

CATEGORIES = [
    "garbage",
    "pothole",
    "drainage",
    "streetlight",
    "water_leakage",
    "other",
]


def generate_garbage_image(size=(224, 224)) -> Image.Image:
    """Generates an image with scattered multi-colored refuse, bins, and dirty ground."""
    img = Image.new("RGB", size, (random.randint(60, 90), random.randint(55, 80), random.randint(45, 70)))
    draw = ImageDraw.Draw(img)
    
    # Ground noise
    for _ in range(300):
        x, y = random.randint(0, size[0]), random.randint(0, size[1])
        r = random.randint(2, 6)
        color = (random.randint(40, 110), random.randint(40, 100), random.randint(30, 80))
        draw.ellipse([x, y, x + r, y + r], fill=color)

    # Garbage pile / items (plastics, cartons, bags)
    colors = [
        (220, 50, 50),   # Red plastic
        (50, 120, 220),  # Blue tarp/bag
        (230, 220, 50),  # Yellow wrapper
        (240, 240, 240), # White paper/polystyrene
        (40, 40, 40),    # Black trash bag
        (140, 90, 40),   # Cardboard
    ]
    for _ in range(40):
        x = random.randint(20, size[0] - 50)
        y = random.randint(40, size[1] - 50)
        w, h = random.randint(10, 40), random.randint(10, 35)
        c = random.choice(colors)
        if random.random() > 0.5:
            draw.rectangle([x, y, x + w, y + h], fill=c)
        else:
            draw.polygon([(x, y), (x + w, y + random.randint(-5, 5)), (x + w - 5, y + h), (x - 5, y + h - 5)], fill=c)

    return img.filter(ImageFilter.GaussianBlur(radius=0.5))


def generate_pothole_image(size=(224, 224)) -> Image.Image:
    """Generates an image with gray asphalt texture and dark, irregular craters."""
    # Gray road base
    img = Image.new("RGB", size, (random.randint(90, 120), random.randint(90, 120), random.randint(95, 125)))
    draw = ImageDraw.Draw(img)

    # Road grain
    for _ in range(400):
        x, y = random.randint(0, size[0]), random.randint(0, size[1])
        c = random.randint(70, 140)
        draw.point((x, y), fill=(c, c, c))

    # Dark pothole crater
    cx, cy = size[0] // 2 + random.randint(-20, 20), size[1] // 2 + random.randint(-20, 20)
    rx, ry = random.randint(35, 65), random.randint(25, 45)

    # Irregular polygon for crater edge
    points = []
    num_pts = 16
    for i in range(num_pts):
        angle = (2 * math.pi * i) / num_pts
        r_var = random.uniform(0.75, 1.25)
        px = cx + int(rx * r_var * math.cos(angle))
        py = cy + int(ry * r_var * math.sin(angle))
        points.append((px, py))

    # Inner dark pit and gravel
    draw.polygon(points, fill=(random.randint(25, 45), random.randint(20, 40), random.randint(20, 35)))
    for _ in range(60):
        gx = cx + random.randint(-rx + 10, rx - 10)
        gy = cy + random.randint(-ry + 10, ry - 10)
        draw.ellipse([gx, gy, gx + random.randint(2, 5), gy + random.randint(2, 5)], fill=(random.randint(50, 80), random.randint(50, 80), random.randint(50, 80)))

    return img.filter(ImageFilter.GaussianBlur(radius=0.6))


def generate_drainage_image(size=(224, 224)) -> Image.Image:
    """Generates an image with concrete curb, open drain channel, and dark/greenish wastewater."""
    img = Image.new("RGB", size, (random.randint(110, 135), random.randint(110, 135), random.randint(110, 135)))
    draw = ImageDraw.Draw(img)

    # Road / sidewalk split line
    split_y = random.randint(70, 110)
    draw.rectangle([0, split_y, size[0], size[1]], fill=(random.randint(30, 50), random.randint(45, 65), random.randint(35, 55)))

    # Gutter channel / iron grate lines
    for x in range(10, size[0] - 10, 18):
        draw.rectangle([x, split_y + 10, x + 8, size[1] - 15], fill=(random.randint(15, 30), random.randint(20, 35), random.randint(20, 35)))

    # Stagnant water highlights
    for _ in range(50):
        wx = random.randint(0, size[0])
        wy = random.randint(split_y, size[1])
        draw.line([(wx, wy), (wx + random.randint(5, 15), wy)], fill=(random.randint(60, 90), random.randint(100, 140), random.randint(80, 120)), width=2)

    return img.filter(ImageFilter.GaussianBlur(radius=0.5))


def generate_streetlight_image(size=(224, 224)) -> Image.Image:
    """Generates an image of a vertical metal pole, cross-arm, lamp fixture against sky."""
    # Sky background (day or evening)
    sky_top = (random.randint(80, 150), random.randint(130, 190), random.randint(200, 245))
    sky_bottom = (random.randint(180, 220), random.randint(200, 230), random.randint(230, 255))
    img = Image.new("RGB", size, sky_bottom)
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(size[1]):
        t = y / size[1]
        r = int(sky_top[0] * (1 - t) + sky_bottom[0] * t)
        g = int(sky_top[1] * (1 - t) + sky_bottom[1] * t)
        b = int(sky_top[2] * (1 - t) + sky_bottom[2] * t)
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))

    # Metallic pole
    pole_x = random.randint(90, 130)
    draw.rectangle([pole_x, 40, pole_x + 12, size[1]], fill=(random.randint(50, 70), random.randint(50, 70), random.randint(55, 75)))
    
    # Arm & Lamp Fixture
    draw.line([(pole_x + 6, 60), (pole_x + 55, 45)], fill=(random.randint(40, 60), random.randint(40, 60), random.randint(45, 65)), width=6)
    draw.polygon([(pole_x + 45, 42), (pole_x + 75, 40), (pole_x + 70, 56), (pole_x + 50, 56)], fill=(random.randint(200, 240), random.randint(200, 230), random.randint(180, 210)))

    return img.filter(ImageFilter.GaussianBlur(radius=0.5))


def generate_water_leakage_image(size=(224, 224)) -> Image.Image:
    """Generates an image with a pipeline joint, water spray/gush, and blue/reflective puddle."""
    img = Image.new("RGB", size, (random.randint(85, 110), random.randint(85, 110), random.randint(90, 115)))
    draw = ImageDraw.Draw(img)

    # Water puddle spreading
    draw.ellipse([20, 80, size[0] - 20, size[1] - 20], fill=(random.randint(60, 100), random.randint(110, 160), random.randint(180, 230)))

    # Metal pipe
    pipe_y = random.randint(60, 90)
    draw.rectangle([0, pipe_y, size[0], pipe_y + 24], fill=(random.randint(80, 110), random.randint(100, 130), random.randint(120, 150)))

    # Burst spray / bubbles
    for _ in range(80):
        sx = random.randint(size[0] // 2 - 30, size[0] // 2 + 30)
        sy = random.randint(pipe_y - 25, pipe_y + 40)
        r = random.randint(2, 7)
        draw.ellipse([sx, sy, sx + r, sy + r], fill=(240, 245, 255))

    return img.filter(ImageFilter.GaussianBlur(radius=0.5))


def generate_other_image(size=(224, 224)) -> Image.Image:
    """Generates non-civic defect control scenes (trees, clean road, building walls)."""
    choice = random.choice(["greenery", "wall", "clean_road"])
    if choice == "greenery":
        img = Image.new("RGB", size, (random.randint(30, 60), random.randint(110, 160), random.randint(40, 70)))
        draw = ImageDraw.Draw(img)
        for _ in range(120):
            x, y = random.randint(0, size[0]), random.randint(0, size[1])
            draw.ellipse([x, y, x + random.randint(10, 30), y + random.randint(10, 30)], fill=(random.randint(20, 80), random.randint(130, 200), random.randint(30, 90)))
    elif choice == "wall":
        img = Image.new("RGB", size, (random.randint(180, 210), random.randint(170, 200), random.randint(150, 180)))
        draw = ImageDraw.Draw(img)
        for y in range(0, size[1], 15):
            draw.line([(0, y), (size[0], y)], fill=(140, 130, 120), width=1)
    else:
        img = Image.new("RGB", size, (130, 130, 130))
        draw = ImageDraw.Draw(img)
        # Yellow lane divider
        draw.rectangle([size[0] // 2 - 4, 0, size[0] // 2 + 4, size[1]], fill=(230, 200, 30))

    return img.filter(ImageFilter.GaussianBlur(radius=0.5))


GENERATORS = {
    "garbage": generate_garbage_image,
    "pothole": generate_pothole_image,
    "drainage": generate_drainage_image,
    "streetlight": generate_streetlight_image,
    "water_leakage": generate_water_leakage_image,
    "other": generate_other_image,
}


def build_vision_dataset(samples_per_class: int = 150):
    for split in ["train", "val", "test"]:
        for cat in CATEGORIES:
            os.makedirs(OUTPUT_IMAGE_DIR / split / cat, exist_ok=True)

    print("============================================================")
    print("      NagarIQ Computer Vision Dataset Preparation (Phase 5) ")
    print("============================================================")

    # Split: 70% train (105), 15% val (22), 15% test (23) per class
    train_n = int(samples_per_class * 0.70)
    val_n = int(samples_per_class * 0.15)
    test_n = samples_per_class - train_n - val_n

    total_count = 0
    for cat in CATEGORIES:
        gen_fn = GENERATORS[cat]
        print(f"[*] Generating {samples_per_class} visual samples for class '{cat}'...")

        for i in range(samples_per_class):
            img = gen_fn()
            if i < train_n:
                split = "train"
                idx = i
            elif i < train_n + val_n:
                split = "val"
                idx = i - train_n
            else:
                split = "test"
                idx = i - train_n - val_n

            filename = f"{cat}_{split}_{idx:04d}.jpg"
            img.save(OUTPUT_IMAGE_DIR / split / cat / filename, format="JPEG", quality=90)
            total_count += 1

    print("------------------------------------------------------------")
    print(f"[+] Total images generated: {total_count}")
    print(f"    - Train: {train_n * len(CATEGORIES)} ({train_n}/class)")
    print(f"    - Val:   {val_n * len(CATEGORIES)} ({val_n}/class)")
    print(f"    - Test:  {test_n * len(CATEGORIES)} ({test_n}/class)")
    print(f"[*] Output directory: {OUTPUT_IMAGE_DIR}")
    print("============================================================")


if __name__ == "__main__":
    build_vision_dataset(samples_per_class=120)
