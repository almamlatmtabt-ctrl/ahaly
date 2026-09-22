"""
Script v2: 
The issue: black watches blend with black background via flood-fill.
Solution: Instead of flood-fill, use a simple pixel-level approach:
- Background = pixels where ALL channels are <= threshold (1)
- Watch = everything else
This works because the background is pure black (0,0,0) or (1,1,1) at corners.
The watch, even if black, has some variation (highlights, reflections, etc.)
that makes its pixels not exactly (0,0,0).
"""

from PIL import Image, ImageDraw
import numpy as np
import os
from scipy.ndimage import gaussian_filter, binary_fill_holes, binary_opening, binary_closing


def create_gray_card(width, height):
    """Create a gray rounded rectangle card in the center of a white canvas"""
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Gray rounded rectangle card with padding
    padding = 50
    corner_radius = 50
    x0 = padding
    y0 = padding
    x1 = width - padding
    y1 = height - padding
    
    # Light gray color for the card
    gray_color = (215, 215, 215)
    border_color = (185, 185, 185)
    
    draw.rounded_rectangle([x0, y0, x1, y1], radius=corner_radius, fill=gray_color, outline=border_color, width=2)
    
    return np.array(img)


def get_watch_mask(watch_arr):
    """
    Direct pixel-level mask: a pixel is background only if ALL channels <= 1.
    Everything else is the watch.
    Then use morphological operations to clean up.
    """
    h, w = watch_arr.shape[:2]
    
    # Background = all channels <= 1
    is_bg = (watch_arr[:,:,0] <= 1) & (watch_arr[:,:,1] <= 1) & (watch_arr[:,:,2] <= 1)
    
    # Watch = NOT background
    watch_mask = ~is_bg
    
    # Clean up: 
    # 1. Close small gaps in the watch (small black spots inside the watch)
    watch_mask = binary_closing(watch_mask, structure=np.ones((5,5)))
    
    # 2. Remove tiny isolated pixels outside the watch
    watch_mask = binary_opening(watch_mask, structure=np.ones((3,3)))
    
    # 3. Fill holes inside the watch
    watch_mask = binary_fill_holes(watch_mask, structure=np.ones((5,5)))
    
    return watch_mask


def process_watch_image(watch_path, output_path):
    """Process a single watch image"""
    watch_img = Image.open(watch_path).convert('RGB')
    width, height = watch_img.size
    print(f"Processing {watch_path}: {width}x{height}")
    
    # Create gray card background
    gray_card = create_gray_card(width, height)
    
    watch_arr = np.array(watch_img).astype(np.float64)
    card_arr = gray_card.astype(np.float64)
    
    # Get watch mask
    watch_mask = get_watch_mask(watch_arr)
    
    # Feather edges for smooth blending
    mask_float = watch_mask.astype(np.float64)
    feathered_mask = gaussian_filter(mask_float, sigma=2.0)
    feathered_mask = np.clip(feathered_mask, 0, 1)
    
    # Add soft shadow under the watch
    shadow_mask = gaussian_filter(mask_float, sigma=20)
    shadow_factor = np.expand_dims(shadow_mask * 0.15, axis=2)
    
    # Card with shadow
    shadowed_card = card_arr * (1 - shadow_factor)
    
    # Blend watch on top of card
    result = watch_arr * np.expand_dims(feathered_mask, axis=2) + shadowed_card * np.expand_dims(1 - feathered_mask, axis=2)
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
        output_path = os.path.join(images_dir, filename.replace('.jpg', '_white.jpg'))
        
        if os.path.exists(input_path):
            process_watch_image(input_path, output_path)
        else:
            print(f"Warning: {input_path} not found")
    
    print("\nAll images processed!")


if __name__ == "__main__":
    main()
