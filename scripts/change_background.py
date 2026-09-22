"""
Script to change the black background of watch images to a sunrise background.
For watch1.jpg which has yellow outlines, we use color-based segmentation.
For other images, we use threshold-based segmentation to remove black background.
"""

from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import numpy as np
import os

# Sunrise background colors - create a gradient sunrise image
def create_sunrise_background(width, height):
    """Create a beautiful sunrise background gradient"""
    img = Image.new('RGB', (width, height))
    pixels = img.load()
    
    for y in range(height):
        ratio = y / height
        if ratio < 0.15:
            # Top: deep blue/purple sky
            r = int(30 + ratio * 200)
            g = int(20 + ratio * 100)
            b = int(80 + ratio * 300)
        elif ratio < 0.35:
            # Upper middle: orange/red sky
            t = (ratio - 0.15) / 0.20
            r = int(230 + t * 25)
            g = int(120 + t * 80)
            b = int(380 - t * 250)
        elif ratio < 0.55:
            # Middle: bright orange/gold
            t = (ratio - 0.35) / 0.20
            r = int(255 - t * 50)
            g = int(200 - t * 50)
            b = int(130 - t * 80)
        elif ratio < 0.75:
            # Lower middle: golden/green grass hint
            t = (ratio - 0.55) / 0.20
            r = int(205 - t * 130)
            g = int(150 + t * 50)
            b = int(50 + t * 20)
        else:
            # Bottom: green/nature
            t = (ratio - 0.75) / 0.25
            r = int(75 - t * 30)
            g = int(200 + t * 55)
            b = int(70 - t * 20)
        
        for x in range(width):
            pixels[x, y] = (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))
    
    # Add sun glow in the center
    cx, cy = width // 2, int(height * 0.35)
    for y in range(height):
        for x in range(width):
            dist = np.sqrt((x - cx)**2 + (y - cy)**2)
            glow_strength = max(0, 1 - dist / (width * 0.4))
            if glow_strength > 0:
                r, g, b = pixels[x, y]
                glow_r = int(r + glow_strength * 60)
                glow_g = int(g + glow_strength * 40)
                glow_b = int(b + glow_strength * 20)
                pixels[x, y] = (min(255, glow_r), min(255, glow_g), min(255, glow_b))
    
    return img


def remove_black_background_watch1(img):
    """Remove background from watch1.jpg which has yellow outline markers"""
    arr = np.array(img)
    
    # The background is black (very low values)
    # Yellow outline pixels have high R, high G, low B
    # We want to keep the watch (including yellow outlines) and remove black
    
    # Create mask: keep pixels that are NOT black
    brightness = np.mean(arr[:,:,:3], axis=2)
    mask = brightness > 30  # Keep anything brighter than 30
    
    # Also check for yellow outline pixels (high R, high G, low B)
    yellow_mask = (arr[:,:,0] > 150) & (arr[:,:,1] > 150) & (arr[:,:,2] < 100)
    
    # Combined mask: keep non-black OR yellow outlines
    combined_mask = mask | yellow_mask
    
    return combined_mask


def remove_black_background_other(img):
    """Remove black background from other watch images"""
    arr = np.array(img)
    
    # Create mask based on brightness
    brightness = np.mean(arr[:,:,:3], axis=2)
    
    # For these images, the background is pure black and the watch has some detail
    # Use a slightly higher threshold to catch dark edges of the watch
    mask = brightness > 20
    
    # Also keep pixels that are clearly not black (any color channel significantly above 0)
    color_mask = (arr[:,:,0] > 25) | (arr[:,:,1] > 25) | (arr[:,:,2] > 25)
    
    # Combined: keep if bright enough OR has some color
    combined_mask = color_mask & mask
    
    # For areas that are very dark but have some color variation (watch edges)
    # Use a more sophisticated approach
    dark_color_mask = brightness <= 20
    saturation = np.max(arr[:,:,:3], axis=2) - np.min(arr[:,:,:3], axis=2)
    dark_with_color = dark_color_mask & (saturation > 10)
    combined_mask = combined_mask | dark_with_color
    
    return combined_mask


def blend_watch_with_background(watch_img, background_img, mask):
    """Blend the watch image with the sunrise background using the mask"""
    watch_arr = np.array(watch_img).astype(float)
    bg_arr = np.array(background_img).astype(float)
    mask_float = mask.astype(float)
    
    # Apply slight feathering to the mask edges for smoother blend
    from scipy.ndimage import gaussian_filter
    feathered_mask = gaussian_filter(mask_float, sigma=3)
    
    # Blend
    result = watch_arr * np.expand_dims(feathered_mask, axis=2) + bg_arr * np.expand_dims(1 - feathered_mask, axis=2)
    result = result.astype(np.uint8)
    
    return Image.fromarray(result)


def process_watch_image(watch_path, output_path, is_watch1=False):
    """Process a single watch image: remove background and add sunrise"""
    watch_img = Image.open(watch_path).convert('RGB')
    width, height = watch_img.size
    
    print(f"Processing {watch_path}: {width}x{height}")
    
    # Create sunrise background
    sunrise_bg = create_sunrise_background(width, height)
    
    # Remove background
    if is_watch1:
        mask = remove_black_background_watch1(watch_img)
    else:
        mask = remove_black_background_other(watch_img)
    
    # Blend
    result = blend_watch_with_background(watch_img, sunrise_bg, mask)
    
    # Save
    result.save(output_path, quality=95)
    print(f"  Saved to {output_path}")


def main():
    images_dir = "/home/ubuntu/mashreq/images"
    
    # Process all 9 watch images
    watch_files = [
        ("watch1.jpg", True),   # Has yellow outlines
        ("watch2.jpg", False),
        ("watch3.jpg", False),
        ("watch4.jpg", False),
        ("watch5.jpg", False),
        ("watch6.jpg", False),
        ("watch7.jpg", False),
        ("watch8.jpg", False),
        ("watch9.jpg", False),
    ]
    
    for filename, is_watch1 in watch_files:
        input_path = os.path.join(images_dir, filename)
        output_path = os.path.join(images_dir, filename.replace('.jpg', '_sunrise.jpg'))
        
        if os.path.exists(input_path):
            process_watch_image(input_path, output_path, is_watch1)
        else:
            print(f"Warning: {input_path} not found")
    
    print("\nAll images processed!")


if __name__ == "__main__":
    main()
