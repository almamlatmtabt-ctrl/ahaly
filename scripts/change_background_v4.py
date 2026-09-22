"""
Script v4: Create realistic sunrise background images using PIL drawing.
Better watch-background separation with morphological operations.
"""

from PIL import Image, ImageFilter, ImageDraw
import numpy as np
import os
from scipy.ndimage import gaussian_filter, binary_dilation, binary_erosion

def create_sunrise_landscape(width, height):
    """Create a realistic sunrise landscape with sky, sun, and ground"""
    img = np.zeros((height, width, 3), dtype=np.float64)
    
    # Sky gradient - from dark blue at top to warm orange near horizon
    for y in range(height):
        t = y / height  # 0 = top, 1 = bottom
        horizon = 0.62  # horizon line position
        
        if t < horizon:
            # Sky above horizon
            sky_t = t / horizon  # 0 at top, 1 at horizon
            
            # Interpolate colors
            if sky_t < 0.1:
                # Deep space blue
                r = 12 + sky_t * 250
                g = 8 + sky_t * 180
                b = 40 + sky_t * 400
            elif sky_t < 0.25:
                # Blue-purple transition
                s = (sky_t - 0.1) / 0.15
                r = 262 + s * 80
                g = 188 + s * 60
                b = 440 - s * 180
            elif sky_t < 0.45:
                # Pink-magenta
                s = (sky_t - 0.25) / 0.20
                r = 342 + s * 60
                g = 248 + s * 30
                b = 260 - s * 80
            elif sky_t < 0.65:
                # Orange-red
                s = (sky_t - 0.45) / 0.20
                r = 402 + s * 30
                g = 278 + s * 40
                b = 180 - s * 40
            elif sky_t < 0.85:
                # Bright golden orange
                s = (sky_t - 0.65) / 0.20
                r = 432 - s * 30
                g = 318 + s * 20
                b = 140 - s * 30
            else:
                # Near horizon - warm gold
                s = (sky_t - 0.85) / 0.15
                r = 402 + s * 50
                g = 338 - s * 20
                b = 110 + s * 20
            
            # Add subtle cloud-like variation
            for x in range(0, width, 2):
                cloud_var = (np.sin(x * 0.008 + y * 0.005) * np.cos(x * 0.003 - y * 0.01) + 1) * 0.5
                r += cloud_var * 8
                g += cloud_var * 5
                b += cloud_var * 3
            
            img[y, :] = [min(255, r), min(255, g), min(255, b)]
        else:
            # Below horizon - warm golden ground
            ground_t = (t - horizon) / (1 - horizon)
            r = 200 - ground_t * 60
            g = 160 + ground_t * 40
            b = 60 + ground_t * 30
            
            # Add texture variation
            for x in range(0, width, 2):
                ground_var = (np.sin(x * 0.01 + y * 0.02) + 1) * 0.5
                r += ground_var * 5
                g += ground_var * 8
                b += ground_var * 2
            
            img[y, :] = [min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b))]
    
    # Add sun
    cx, cy = int(width * 0.5), int(height * 0.38)
    ys, xs = np.indices((height, width))
    dist = np.sqrt((xs - cx)**2 + (ys - cy)**2)
    
    # Sun core
    sun_core = np.exp(-dist**2 / (2 * (width * 0.06)**2))
    img[:,:,0] = np.clip(img[:,:,0] + sun_core * 100, 0, 255)
    img[:,:,1] = np.clip(img[:,:,1] + sun_core * 80, 0, 255)
    img[:,:,2] = np.clip(img[:,:,2] + sun_core * 30, 0, 255)
    
    # Sun halo
    sun_halo = np.exp(-dist**2 / (2 * (width * 0.18)**2))
    img[:,:,0] = np.clip(img[:,:,0] + sun_halo * 40, 0, 255)
    img[:,:,1] = np.clip(img[:,:,1] + sun_halo * 30, 0, 255)
    img[:,:,2] = np.clip(img[:,:,2] + sun_halo * 10, 0, 255)
    
    # Warm ambient light
    warm_glow = np.exp(-dist**2 / (2 * (width * 0.4)**2))
    img[:,:,0] = np.clip(img[:,:,0] + warm_glow * 15, 0, 255)
    img[:,:,1] = np.clip(img[:,:,1] + warm_glow * 10, 0, 255)
    
    return img.astype(np.uint8)


def separate_watch_from_background(watch_arr):
    """Better separation of watch from black background using HSV"""
    r = watch_arr[:,:,0].astype(np.float64)
    g = watch_arr[:,:,1].astype(np.float64)
    b = watch_arr[:,:,2].astype(np.float64)
    
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    
    value = max_c
    saturation = np.zeros_like(r)
    mask = max_c > 1
    saturation[mask] = (max_c[mask] - min_c[mask]) / max_c[mask]
    
    # Detect non-black pixels
    # Watch has: brightness > 10 OR saturation > 0.03
    is_watch = (value > 12) | (saturation > 0.035)
    
    # Clean up: remove small isolated black spots inside the watch (holes)
    # and remove small isolated non-black spots outside (noise)
    is_watch = binary_erosion(is_watch, iterations=1)
    is_watch = binary_dilation(is_watch, iterations=2)
    
    return is_watch


def process_watch_image(watch_path, output_path):
    """Process a single watch image"""
    watch_img = Image.open(watch_path).convert('RGB')
    width, height = watch_img.size
    print(f"Processing {watch_path}: {width}x{height}")
    
    # Create sunrise background
    sunrise_bg = create_sunrise_landscape(width, height)
    
    watch_arr = np.array(watch_img).astype(np.float64)
    bg_arr = sunrise_bg.astype(np.float64)
    
    # Separate watch from background
    watch_mask = separate_watch_from_background(watch_arr)
    
    # Feather the mask edges
    mask_float = watch_mask.astype(np.float64)
    feathered_mask = gaussian_filter(mask_float, sigma=2.5)
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
