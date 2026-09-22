"""
Script to change watch images: 
- Background becomes white
- A rounded rectangle (card) behind the watch with gray color
"""

from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import os
from scipy.ndimage import gaussian_filter, binary_fill_holes
from collections import deque


def get_background_mask(watch_arr, threshold=0):
    """
    Flood fill from edges. Only pure black (or near-pure black) pixels.
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


def create_gray_card(width, height):
    """Create a gray rounded rectangle card in the center of a white canvas"""
    # White background
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Gray rounded rectangle card with padding
    padding = 60
    corner_radius = 40
    x0 = padding
    y0 = padding
    x1 = width - padding
    y1 = height - padding
    
    # Light gray color
    gray_color = (220, 220, 220)
    # Slightly darker border
    border_color = (180, 180, 180)
    
    draw.rounded_rectangle([x0, y0, x1, y1], radius=corner_radius, fill=gray_color, outline=border_color, width=2)
    
    return np.array(img)


def process_watch_image(watch_path, output_path):
    """Process a single watch image: white background with gray card"""
    watch_img = Image.open(watch_path).convert('RGB')
    width, height = watch_img.size
    print(f"Processing {watch_path}: {width}x{height}")
    
    # Create gray card background
    gray_card = create_gray_card(width, height)
    
    watch_arr = np.array(watch_img).astype(np.float64)
    card_arr = gray_card.astype(np.float64)
    
    # Check corner pixel to determine threshold
    corner_val = np.mean(watch_arr[0, 0])
    threshold = max(0, int(corner_val) + 1)
    if threshold > 1:
        threshold = 1  # Cap at 1 to be safe
    print(f"  Corner avg: {corner_val:.1f}, threshold: {threshold}")
    
    # Get background mask (black pixels connected to edges)
    bg_mask = get_background_mask(watch_arr, threshold=threshold)
    
    # Clean up background mask
    bg_mask = binary_fill_holes(bg_mask, structure=np.ones((3,3)))
    
    # Watch mask = NOT background
    watch_mask = ~bg_mask
    watch_mask = binary_fill_holes(watch_mask, structure=np.ones((3,3)))
    
    # Feather edges for smooth blending
    mask_float = watch_mask.astype(np.float64)
    feathered_mask = gaussian_filter(mask_float, sigma=2.5)
    feathered_mask = np.clip(feathered_mask, 0, 1)
    
    # Add shadow effect for the watch
    shadow_mask = gaussian_filter(mask_float, sigma=15)
    shadow_mask = np.clip(shadow_mask * 0.3, 0, 1)
    
    # First blend shadow onto card
    shadow_factor = np.expand_dims(shadow_mask * 0.4, axis=2)
    shadowed_card = card_arr * (1 - shadow_factor) + np.zeros_like(card_arr) * shadow_factor
    
    # Then blend watch on top
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
