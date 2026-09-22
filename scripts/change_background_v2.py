"""
Script to change the black background of watch images to a sunrise background.
Uses a more robust approach: detect black pixels and replace with background.
"""

from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import numpy as np
import os

def create_sunrise_background(width, height):
    """Create a beautiful sunrise background gradient"""
    img = Image.new('RGB', (width, height))
    pixels = img.load()
    
    for y in range(height):
        ratio = y / height
        if ratio < 0.12:
            # Top: deep blue/purple sky
            r = int(25 + ratio * 150)
            g = int(15 + ratio * 80)
            b = int(70 + ratio * 250)
        elif ratio < 0.30:
            # Upper middle: orange/red sky
            t = (ratio - 0.12) / 0.18
            r = int(175 + t * 80)
            g = int(95 + t * 105)
            b = int(320 - t * 220)
        elif ratio < 0.50:
            # Middle: bright orange/gold
            t = (ratio - 0.30) / 0.20
            r = int(255 - t * 40)
            g = int(200 - t * 40)
            b = int(100 - t * 50)
        elif ratio < 0.70:
            # Lower middle: golden/green grass hint
            t = (ratio - 0.50) / 0.20
            r = int(215 - t * 140)
            g = int(160 + t * 40)
            b = int(50 + t * 30)
        else:
            # Bottom: green nature
            t = (ratio - 0.70) / 0.30
            r = int(75 - t * 35)
            g = int(200 + t * 55)
            b = int(80 - t * 30)
        
        for x in range(width):
            pixels[x, y] = (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))
    
    # Add sun glow
    cx, cy = width // 2, int(height * 0.33)
    arr = np.array(img).astype(float)
    ys, xs = np.indices((height, width))
    dist = np.sqrt((xs - cx)**2 + (ys - cy)**2)
    max_dist = width * 0.45
    glow = np.clip(1 - dist / max_dist, 0, 1) ** 2
    
    arr[:,:,0] += glow * 50
    arr[:,:,1] += glow * 30
    arr[:,:,2] += glow * 15
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    
    return Image.fromarray(arr)


def is_black_pixel(pixel, threshold=25):
    """Check if a pixel is black (all channels below threshold)"""
    r, g, b = pixel[0], pixel[1], pixel[2]
    return r < threshold and g < threshold and b < threshold


def process_watch_image(watch_path, output_path):
    """Process a single watch image: remove black background and add sunrise"""
    watch_img = Image.open(watch_path).convert('RGB')
    width, height = watch_img.size
    print(f"Processing {watch_path}: {width}x{height}")
    
    # Create sunrise background
    sunrise_bg = create_sunrise_background(width, height)
    
    watch_arr = np.array(watch_img)
    bg_arr = np.array(sunrise_bg)
    
    # Create mask: True where pixel is NOT black (i.e., it's part of the watch)
    brightness = np.mean(watch_arr[:,:,:3], axis=2)
    
    # Also check saturation for dark but colored pixels (watch edges)
    max_channel = np.max(watch_arr[:,:,:3], axis=2)
    min_channel = np.min(watch_arr[:,:,:3], axis=2)
    saturation = max_channel - min_channel
    
    # A pixel is part of the watch if:
    # 1. It's bright enough, OR
    # 2. It has significant color saturation (colored pixels even if dark)
    brightness_mask = brightness > 25
    saturation_mask = saturation > 8
    
    # Combined mask
    watch_mask = brightness_mask | saturation_mask
    
    # Apply gaussian blur to the mask for smoother edges
    from scipy.ndimage import gaussian_filter
    mask_float = watch_mask.astype(float)
    feathered_mask = gaussian_filter(mask_float, sigma=4)
    
    # Blend: watch where mask is strong, background where mask is weak
    result = watch_arr * np.expand_dims(feathered_mask, axis=2) + bg_arr * np.expand_dims(1 - feathered_mask, axis=2)
    result = result.astype(np.uint8)
    
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
