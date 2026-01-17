import numpy as np
from PIL import Image

def center_crop(img_path, crop_size=224):
    # Step 1: load image
    image = Image.open(img_path).convert("RGB")

    # Step 2: center crop
    w, h = image.size
    left = (w - crop_size) // 2
    top = (h - crop_size) // 2
    right = left + crop_size
    bottom = top + crop_size
    image = image.crop((left, top, right, bottom))  # PIL Image, size (224, 224)

    # Step 3: to_numpy
    image = np.array(image).astype(np.float32) / 255.0  # (H, W, C)

    # Step 4: norm
    mean = np.array([0.485, 0.456, 0.406])
    std  = np.array([0.229, 0.224, 0.225])
    image = (image - mean) / std  # (H, W, C)
    image = image.transpose(2, 0, 1) # (C, H, W)
    return image[None] # (1, C, H, W)

# ************* ToDo, resize short side *************
def resize_short_side(img_path, target_size=224):
    # Step 1: load image
    image = Image.open(img_path).convert("RGB")

    # Step 2: aspect-preserving resize so that the shorter side == target_size
    ps = 14
    w, h = image.size
    if w == 0 or h == 0:
        raise ValueError("Invalid image size")
    if h < w:
        new_h = target_size
        new_w = int(round(w * (target_size / h)))
    else:
        new_w = target_size
        new_h = int(round(h * (target_size / w)))
    image = image.resize((new_w, new_h), Image.BICUBIC)

    # Step 2.1: center-crop to exactly target_size x target_size (224x224)
    # This stabilizes the patch grid to 16x16 and avoids expensive pos-encoding interpolation.
    left = max((new_w - target_size) // 2, 0)
    top = max((new_h - target_size) // 2, 0)
    right = left + target_size
    bottom = top + target_size
    image = image.crop((left, top, right, bottom))

    # Step 2.2: ensure sides are multiples of patch size (target_size=224 divisible by 14)
    # No-op here; kept for clarity.

    # Step 3: to_numpy
    image = np.array(image).astype(np.float32) / 255.0  # (H, W, C)

    # Step 4: norm
    mean = np.array([0.485, 0.456, 0.406])
    std  = np.array([0.229, 0.224, 0.225])
    image = (image - mean) / std  # (H, W, C)
    image = image.transpose(2, 0, 1) # (C, H, W)
    return image[None] # (1, C, H, W)