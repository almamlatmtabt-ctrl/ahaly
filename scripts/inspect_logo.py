from PIL import Image
im = Image.open('static_nbe_logo_full.png')
print('mode=', im.mode, 'size=', im.size)
print('info=', im.info)
rgba = im.convert('RGBA')
alpha = rgba.getchannel('A')
print('alpha_bbox=', alpha.getbbox(), 'alpha_extrema=', alpha.getextrema())
print('corners=', [rgba.getpixel(pt) for pt in [(0,0),(10,10),(rgba.width-1,rgba.height-1)]])
