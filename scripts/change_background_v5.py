"""
Script v5: Better approach - detect PURE black background pixels only.
The watch face has white/dark areas but the BACKGROUND is pure black (0,0,0).
Use a flood-fill approach starting from corners to identify background.
"""

from PIL import Image, ImageFilter
import numpy as np
import os
from scipy.ndimage import gaussian_filter, label, binary_fill_holes

def create_sunrise_landscape(width, height):
    """Create a realistic sunrise landscape"""
    img = np.zeros((height, width, 3), dtype=np.float64)
    
    horizon_y = int(height * 0.62)
    
    # Sky part (above horizon)
    for y in range(horizon_y):
        t = y / horizon_y
        for x in range(width):
            # Base gradient
            if t < 0.1:
                base = [18, 12, 55]
            elif t < 0.25:
                s = (t - 0.1) / 0.15
                base = [18 + s*72, 12 + s*58, 55 + s*195]
            elif t < 0.45:
                s = (t - 0.25) / 0.20
                base = [90 + s*120, 70 + s*60, 250 - s*120]
            elif t < 0.65:
                s = (t - 0.45) / 0.20
                base = [210 + s*45, 130 + s*50, 130 - s*30]
            elif t < 0.85:
                s = (t - 0.65) / 0.20
                base = [255 - s*20, 180 + s*40, 100 - s*30]
            else:
                s = (t - 0.85) / 0.15
                base = [235 + s*20, 220 - s*10, 70 + s*30]
            
            # Subtle noise for natural look
            noise = (np.random.random() - 0.5) * 6
            img[y, x] = [min(255, max(0, base[0] + noise)), 
                         min(255, max(0, base[1] + noise)),
                         min(255, max(0, base[2] + noise))]
    
    # Ground part (below horizon)
    for y in range(horizon_y, height):
        t = (y - horizon_y) / (height - horizon_y)
        for x in range(width):
            base = [180 - t*40, 170 + t*30, 60 + t*40]
            noise = (np.random.random() - 0.5) * 5
            img[y, x] = [min(255, max(0, base[0] + noise)),
                         min(255, max(0, base[1] + noise)),
                         min(255, max(0, base[2] + noise))]
    
    # Add sun
    cx, cy = int(width * 0.5), int(height * 0.38)
    ys, xs = np.indices((height, width))
    dist = np.sqrt((xs - cx)**2 + (ys - cy)**2)
    
    # Core
    core = np.exp(-dist**2 / (2 * (width * 0.07)**2))
    img[:,:,0] = np.clip(img[:,:,0] + core * 80, 0, 255)
    img[:,:,1] = np.clip(img[:,:,1] + core * 60, 0, 255)
    img[:,:,2] = np.clip(img[:,:,2] + core * 20, 0, 255)
    
    # Halo
    halo = np.exp(-dist**2 / (2 * (width * 0.2)**2))
    img[:,:,0] = np.clip(img[:,:,0] + halo * 30, 0, 255)
    img[:,:,1] = np.clip(img[:,:,1] + halo * 25, 0, 255)
    img[:,:,2] = np.clip(img[:,:,2] + halo * 10, 0, 255)
    
    return img.astype(np.uint8)


def get_background_mask(watch_arr):
    """
    Use flood fill from corners to identify background.
    Background is connected to corners and is black.
    """
    h, w = watch_arr.shape[:2]
    
    # Create a mask of "very dark" pixels (potential background)
    brightness = np.mean(watch_arr[:,:,:3], axis=2)
    is_dark = brightness < 35
    
    # Flood fill from all 4 corners - any dark pixel connected to a corner is background
    from scipy.ndimage import label
    # Create a marker image
    marker = np.zeros((h, w), dtype=int)
    
    # Mark corners as seeds if they are dark
    seed_value = 1
    corners = [(0, 0), (0, w-1), (h-1, 0), (h-1, w-1)]
    for cy, cx in corners:
        if is_dark[cy, cx]:
            marker[cy, cx] = seed_value
    
    # Use binary propagation from corners
    # Start from corner dark pixels and grow
    visited = np.zeros((h, w), dtype=bool)
    stack = []
    for cy, cx in corners:
        if is_dark[cy, cx]:
            stack.append((cy, cx))
            visited[cy, cx] = True
    
    while stack:
        y, x = stack.pop()
        # Check 4 neighbors
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_dark[ny, nx]:
                visited[ny, nx] = True
                stack.append((ny, nx))
    
    # visited = background pixels (connected to corners and dark)
    background_mask = visited
    
    # Fill any small holes in the background (isolated non-dark pixels in background area)
    # But keep the watch intact
    return background_mask


def process_watch_image(watch_path, output_path):
    """Process a single watch image"""
    watch_img = Image.open(watch_path).convert('RGB')
    width, height = watch_img.size
    print(f"Processing {watch_path}: {width}x{height}")
    
    # Create sunrise background
    sunrise_bg = create_sunrise_landscape(width, height)
    
    watch_arr = np.array(watch_img).astype(np.float64)
    bg_arr = sunrise_bg.astype(np.float64)
    
    # Get background mask (pixels connected to corners that are dark)
    bg_mask = get_background_mask(watch_arr)
    
    # Watch mask = NOT background
    watch_mask = ~bg_mask
    
    # Feather edges
    mask_float = watch_mask.astype(np.float64)
    feathered_mask = gaussian_filter(mask_float, sigma=2.0)
    feathered_mask = np.clip(feathered_mask, 0, 1)
    
    # Blend
    result = watch_arr * np.expand_dims(feathered_mask, axis=2) + bg_arr * np.expand_dims(1 - feathered_mask, axis=2)
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    result_img = Image.fromarray(result)
    result_img.save(output_path, quality=95)
    print(f"  Saved to {output_path}")


def main():
    images_dir = "/home/ubuntu/mashreq/images"
    
    watch_files = [
        "watch1.jpg", "watch2.jpg", "watch3.jpg", "watch4.jpg",
        "watch5.jpg", "watch6.jpg", "watch7.jpg", "watch8.jpg", "watch9.jpg"
    ]
    
    for filename in watch_files:
        input_path = os.path.join(images_dir, filename)
        output_path = os.path.join(images_dir, filename.replace('.jpg', '_sunrise.jpg'))
        
        if os.path.exists(input_path):
            process_watch_image(input_path, output_path)
        else:
            print(f"Warning: {input_path} not found")
    
    print("\nAll images processed!")


if __name__ == "__main__":
    main()
