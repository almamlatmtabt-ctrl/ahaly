"""Analyze pixel values at corners and edges to understand the background"""
from PIL import Image
import numpy as np

# Check watch1.jpg corners
img = np.array(Image.open("/home/ubuntu/mashreq/images/watch1.jpg"))
print("=== watch1.jpg ===")
print(f"Top-left corner (0,0): RGB = {img[0, 0]}")
print(f"Top-right corner (0,-1): RGB = {img[0, -1]}")
print(f"Bottom-left corner (-1,0): RGB = {img[-1, 0]}")
print(f"Bottom-right corner (-1,-1): RGB = {img[-1, -1]}")

# Check a few more edge pixels
for i in range(0, 100, 10):
    print(f"  Left edge y={i}: RGB = {img[i, 0]}")

# Check watch face area (should have dark pixels too)
print(f"\nWatch face center area (600, 600): RGB = {img[600, 600]}")
print(f"Watch strap area (800, 400): RGB = {img[800, 400]}")

# Check brightness distribution
brightness = np.mean(img[:,:,:3], axis=2)
print(f"\nBrightness stats:")
print(f"  Min: {brightness.min():.1f}")
print(f"  Max: {brightness.max():.1f}")
print(f"  Mean: {brightness.mean():.1f}")

# Count pixels by brightness
for thresh in [5, 10, 15, 20, 25, 30, 35, 40]:
    count = np.sum(brightness < thresh)
    pct = count / brightness.size * 100
    print(f"  Pixels with brightness < {thresh}: {count} ({pct:.1f}%)")

print("\n=== watch5.jpg ===")
img5 = np.array(Image.open("/home/ubuntu/mashreq/images/watch5.jpg"))
print(f"Top-left corner (0,0): RGB = {img5[0, 0]}")
print(f"Bottom-right corner (-1,-1): RGB = {img5[-1, -1]}")
brightness5 = np.mean(img5[:,:,:3], axis=2)
print(f"  Min: {brightness5.min():.1f}")
print(f"  Max: {brightness5.max():.1f}")
for thresh in [5, 10, 15, 20, 25, 30, 35, 40]:
    count = np.sum(brightness5 < thresh)
    pct = count / brightness5.size * 100
    print(f"  Pixels with brightness < {thresh}: {count} ({pct:.1f}%)")
