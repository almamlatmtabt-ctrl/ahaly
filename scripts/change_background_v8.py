"""
Script v8: Since the background is pure black (0,0,0) and JPEG compression 
doesn't affect corners, we use threshold=0 (only pure black pixels).
The flood-fill from edges will only follow pure black pixels.
For watch5.jpg which has (1,1,1) at corners, we use threshold=1.
"""

from PIL import Image
import numpy as np
import os
from scipy.ndimage import gaussian_filter, binary_fill_holes
from collections import deque

def create_sunrise_landscape(width, height):
    """Create a beautiful sunrise landscape"""
    img = np.zeros((height, width, 3), dtype=np.float64)
    
    horizon_y = int(height * 0.62)
    
    for y in range(height):
        t = y / height
        for x in range(width):
            if t < horizon_y / height:
                sky_t = t / (horizon_y / height)
                if sky_t < 0.08:
                    base = [15, 10, 50]
                elif sky_t < 0.20:
                    s = (sky_t - 0.08) / 0.12
                    base = [15 + s*55, 10 + s*45, 50 + s*160]
                elif sky_t < 0.38:
                    s = (sky_t - 0.20) / 0.18
                    base = [70 + s*90, 55 + s*55, 210 - s*80]
                elif sky_t < 0.55:
                    s = (sky_t - 0.38) / 0.17
                    base = [160 + s*70, 110 + s*45, 130 - s*30]
                elif sky_t < 0.72:
                    s = (sky_t - 0.55) / 0.17
                    base = [230 + s*25, 155 + s*45, 100 - s*30]
                elif sky_t < 0.88:
                    s = (sky_t - 0.72) / 0.16
                    base = [255 - s*15, 200 + s*20, 70 + s*15]
                else:
                    s = (sky_t - 0.88) / 0.12
                    base = [240 + s*15, 220 - s*10, 85 + s*25]
                
                nx = (np.sin(x * 0.005 + y * 0.003) + 1) * 0.5
                base = [b + nx * 5 for b in base]
            else:
                ground_t = (t - horizon_y / height) / (1 - horizon_y / height)
                base = [200 - ground_t * 50, 180 + ground_t * 20, 70 + ground_t * 50]
                nx = (np.sin(x * 0.008 + y * 0.005) + 1) * 0.5
                base = [b + nx * 4 for b in base]
            
            img[y, x] = [min(255, max(0, base[0])), min(255, max(0, base[1])), min(255, max(0, base[2]))]
    
    # Sun
    cx, cy = int(width * 0.5), int(height * 0.38)
    ys, xs = np.indices((height, width))
    dist = np.sqrt((xs - cx)**2 + (ys - cy)**2)
    
    core = np.exp(-dist**2 / (2 * (width * 0.06)**2))
    img[:,:,0] = np.clip(img[:,:,0] + core * 100, 0, 255)
    img[:,:,1] = np.clip(img[:,:,1] + core * 80, 0, 255)
    img[:,:,2] = np.clip(img[:,:,2] + core * 25, 0, 255)
    
    halo = np.exp(-dist**2 / (2 * (width * 0.22)**2))
    img[:,:,0] = np.clip(img[:,:,0] + halo * 35, 0, 255)
    img[:,:,1] = np.clip(img[:,:,1] + halo * 25, 0, 255)
    img[:,:,2] = np.clip(img[:,:,2] + halo * 8, 0, 255)
    
    return img.astype(np.uint8)


def get_background_mask(watch_arr, threshold=0):
    """
    Flood fill from edges. Only pure black (or near-pure black) pixels.
    threshold=0 means only exact (0,0,0) pixels.
    threshold=1 allows (1,1,1) pixels too.
    """
    h, w = watch_arr.shape[:2]
    
    # Strict: pixel must have ALL channels <= threshold
    is_bg = (watch_arr[:,:,0] <= threshold) & (watch_arr[:,:,1] <= threshold) & (watch_arr[:,:,2] <= threshold)
    
    # BFS from edges
    visited = np.zeros((h, w), dtype=bool)
    queue = deque()
    
    for y in range(h):
        if is_bg[y, 0]:
            queue.append((y, 0)); visited[y, 0] = True
        if is_bg[y, w-1]:
            queue.append((y, w-1)); visited[y, w-1] = True
    for x in range(w):
        if is_bg[0, x]:
            queue.append((0, x)); visited[0, x] = True
        if is_bg[h-1, x]:
            queue.append((h-1, x)); visited[h-1, x] = True
    
    while queue:
        y, x = queue.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_bg[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))
    
    return visited


def process_watch_image(watch_path, output_path):
    """Process a single watch image"""
    watch_img = Image.open(watch_path).convert('RGB')
    width, height = watch_img.size
    print(f"Processing {watch_path}: {width}x{height}")
    
    sunrise_bg = create_sunrise_landscape(width, height)
    watch_arr = np.array(watch_img).astype(np.float64)
    bg_arr = sunrise_bg.astype(np.float64)
    
    # Check corner pixel value to determine threshold
    corner_val = np.mean(watch_arr[0, 0])
    if corner_val <= 0:
        threshold = 0
    else:
        threshold = int(corner_val) + 1
    
    print(f"  Corner pixel avg: {corner_val:.1f}, using threshold: {threshold}")
    
    bg_mask = get_background_mask(watch_arr, threshold=threshold)
    
    # Clean up
    bg_mask = binary_fill_holes(bg_mask, structure=np.ones((3,3)))
    
    # Watch mask
    watch_mask = ~bg_mask
    watch_mask = binary_fill_holes(watch_mask, structure=np.ones((3,3)))
    
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
