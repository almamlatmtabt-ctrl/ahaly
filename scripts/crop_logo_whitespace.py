from PIL import Image, ImageChops

source = Image.open('static_nbe_logo_full.png').convert('RGBA')
background = Image.new('RGBA', source.size, (255, 255, 255, 255))
diff = ImageChops.difference(source, background).convert('L')
# Include a small tolerance so near-white anti-aliased edges are preserved.
bbox = diff.point(lambda value: 255 if value > 12 else 0).getbbox()
if bbox is None:
    raise RuntimeError('Could not detect logo content')
left, top, right, bottom = bbox
pad = 12
left = max(0, left - pad)
top = max(0, top - pad)
right = min(source.width, right + pad)
bottom = min(source.height, bottom + pad)
source.crop((left, top, right, bottom)).save('static_nbe_logo_full.png', optimize=True)
print('cropped_to=', (right-left, bottom-top), 'bbox=', (left, top, right, bottom))
