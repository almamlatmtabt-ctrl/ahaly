"""
Script to change the black background of watch images to a realistic sunrise background.
Uses color-based segmentation with better thresholds and a more natural sunrise gradient.
"""

from PIL import Image
import numpy as np
import os

def create_sunrise_background(width, height):
    """Create a realistic sunrise background with smooth transitions"""
    img = np.zeros((height, width, 3), dtype=np.float64)
    
    for y in range(height):
        t = y / height  # 0 = top, 1 = bottom
        
        if t < 0.08:
            # Deep dark blue sky at top
            img[y, :] = [15, 12, 45]
        elif t < 0.15:
            # Transition to purple
            s = (t - 0.08) / 0.07
            img[y, :] = [15 + s*40, 12 + s*25, 45 - s*15]
        elif t < 0.25:
            # Purple to pink/magenta
            s = (t - 0.15) / 0.10
            img[y, :] = [55 + s*100, 37 + s*50, 30 + s*30]
        elif t < 0.35:
            # Pink to orange-red
            s = (t - 0.25) / 0.10
            img[y, :] = [155 + s*70, 87 + s*60, 60 + s*10]
        elif t < 0.45:
            # Bright orange-red (sun area)
            s = (t - 0.35) / 0.10
            img[y, :] = [225 + s*30, 147 + s*53, 70 + s*20]
        elif t < 0.55:
            # Golden yellow
            s = (t - 0.45) / 0.10
            img[y, :] = [255 - s*30, 200 - s*30, 90 + s*20]
        elif t < 0.65:
            # Transition to warm green/gold
            s = (t - 0.55) / 0.10
            img[y, :] = [225 - s*100, 170 + s*20, 110 - s*40]
        elif t < 0.78:
            # Light green grass
            s = (t - 0.65) / 0.13
            img[y, :] = [125 - s*55, 190 + s*30, 70 + s*20]
        else:
            # Darker green at bottom
            s = (t - 0.78) / 0.22
            img[y, :] = [70 - s*30, 220 - s*40, 90 - s*20]
    
    # Add horizontal variation for clouds/haze
    for y in range(height):
        for x in range(0, width, 4):
            variation = np.sin(x * 0.02 + y * 0.01) * 5 + np.cos(x * 0.01 - y * 0.03) * 3
            img[y, x:x+4, :] += variation
    
    # Add sun glow in center
    cx, cy = width // 2, int(height * 0.40)
    ys, xs = np.indices((height, width))
    dist = np.sqrt((xs - cx)**2 + (ys - cy)**2)
    max_dist = width * 0.5
    
    # Sun core glow
    core_glow = np.exp(-dist**2 / (2 * (width * 0.12)**2))
    img[:,:,0] += core_glow * 40
    img[:,:,1] += core_glow * 20
    img[:,:,2] += core_glow * 10
    
    # Wider ambient glow
    ambient_glow = np.exp(-dist**2 / (2 * (width * 0.3)**2))
    img[:,:,0] += ambient_glow * 20
    img[:,:,1] += ambient_glow * 15
    img[:,:,2] += ambient_glow * 5
    
    return np.clip(img, 0, 255).astype(np.uint8)


def process_watch_image(watch_path, output_path):
    """Process a single watch image: remove black background and add sunrise"""
    watch_img = Image.open(watch_path).convert('RGB')
    width, height = watch_img.size
    print(f"Processing {watch_path}: {width}x{height}")
    
    # Create sunrise background
    sunrise_bg = create_sunrise_background(width, height)
    
    watch_arr = np.array(watch_img).astype(np.float64)
    bg_arr = sunrise_bg.astype(np.float64)
    
    # Detect black pixels using HSV-like approach
    # Convert to HSV manually for better detection
    r, g, b = watch_arr[:,:,0], watch_arr[:,:,1], watch_arr[:,:,2]
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    
    # Value (brightness)
    value = max_c
    
    # Saturation
    saturation = np.where(max_c > 0, (max_c - min_c) / max_c, 0)
    
    # A pixel is part of the watch if:
    # 1. It has significant brightness (V > 15), OR
    # 2. It has significant saturation (S > 0.05) - colored pixels
    # This catches dark metallic parts of the watch
    brightness_threshold = 15
    saturation_threshold = 0.04
    
    watch_mask = (value > brightness_threshold) | (saturation > saturation_threshold)
    
    # Apply feathering for smoother edges
    from scipy.ndimage import gaussian_filter
    mask_float = watch_mask.astype(np.float64)
    feathered_mask = gaussian_filter(mask_float, sigma=3.0)
    
    # Clip feathered mask
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
