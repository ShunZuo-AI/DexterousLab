"""Build the white-blue README cover from manufacturer-published product images."""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'docs/media'
DIRECTORY = MEDIA / 'official-products'
REGULAR = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
BOLD = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'


def cutout(product):
    """Preserve original product colors, using supplied alpha or edge-connected white."""
    path = ROOT / product['local_image']
    if hashlib.sha256(path.read_bytes()).hexdigest() != product['local_sha256']:
        raise ValueError(f'Modified source image: {path}')
    image = Image.open(path).convert('RGBA')
    crop = product.get('crop_fraction')
    if crop:
        w, h = image.size
        image = image.crop((int(crop[0]*w), int(crop[1]*h), int(crop[2]*w), int(crop[3]*h)))
    method = 'Original transparent background'
    if product.get('background_method') == 'grabcut_l20':
        import cv2

        pixels = np.array(image)
        outline = np.array([[268,219],[276,100],[280,87],[286,83],[294,85],[300,94],[300,204],
            [312,202],[312,90],[316,76],[323,72],[331,76],[336,88],[337,204],
            [348,205],[348,103],[351,88],[358,83],[366,88],[371,101],[372,209],
            [381,212],[382,114],[386,100],[394,95],[400,100],[403,112],[403,222],
            [410,229],[412,341],[401,366],[384,391],[382,431],[300,434],
            [297,395],[279,375],[265,352],[246,340],[225,320],[210,285],
            [206,245],[207,222],[212,215],[220,218],[231,232],[238,254],
            [245,277],[263,300],[265,240]])
        silhouette = np.zeros(pixels.shape[:2], dtype=np.uint8)
        cv2.fillPoly(silhouette, [outline], 255)
        # Retain a traced product silhouette; the source scene is never repainted.
        pixels[:,:,3] = np.minimum(pixels[:,:,3], silhouette)
        image = Image.fromarray(pixels)
        method = 'Traced foreground silhouette from official L20 detail-3; no product recoloring'
    if product.get('background_method') == 'largest_alpha_component':
        pixels = np.array(image)
        # These regions are outside the hand in the official ROH dimension diagram.
        pixels[:, 355:, 3] = 0
        pixels[:22, 175:, 3] = 0
        pixels[548:558, 198:, 3] = 0
        expanded = ndimage.binary_dilation(pixels[:,:,3] > 12, iterations=2)
        components, _ = ndimage.label(expanded)
        counts = np.bincount(components.ravel())
        counts[0] = 0
        pixels[components != counts.argmax(), 3] = 0
        image = Image.fromarray(pixels)
        method = 'Remove external ROH dimension annotation regions; keep product RGB unchanged'
    if image.getchannel('A').getextrema()[0] == 255:
        pixels = np.array(image)
        white = (pixels[:, :, :3].min(axis=2) > 242)
        seeds = np.zeros(white.shape, dtype=bool)
        seeds[[0, -1], :] = white[[0, -1], :]
        seeds[:, [0, -1]] = white[:, [0, -1]]
        outside = ndimage.binary_propagation(seeds, mask=white)
        pixels[outside, 3] = 0
        image = Image.fromarray(pixels)
        method = 'Remove edge-connected near-white PDF background; product RGB unchanged'
    box = image.getchannel('A').point(lambda p: 255 if p > 12 else 0).getbbox()
    if not box:
        raise ValueError(f'Empty product image: {product["product_name"]}')
    image = image.crop(box)
    output = DIRECTORY / 'cutouts' / (product['id'] + '.png')
    output.parent.mkdir(exist_ok=True)
    image.save(output, optimize=True)
    return image, {'method': method, 'crop_fraction': crop, 'trim_box_after_crop': list(box),
                   'output': str(output.relative_to(ROOT))}


def text(canvas, xy, value, size, color, face=REGULAR, anchor='lm'):
    ImageDraw.Draw(canvas).text(xy, value, fill=color,
        font=ImageFont.truetype(face, size), anchor=anchor)


def main():
    source = DIRECTORY / 'sources.json'
    manifest = json.loads(source.read_text())
    products = manifest['products']
    frames = {}
    evidence = []
    for product in products:
        frame, operation = cutout(product)
        frames[product['id']] = frame
        evidence.append({'id': product['id'], 'local_sha256': product['local_sha256'], **operation})

    w, h = 2800, 1600
    yy, xx = np.mgrid[0:h, 0:w]
    field = np.exp(-(((xx-1900)/880)**2 + ((yy-760)/900)**2)*1.3)
    colors = np.stack([255-field*29, 255-field*15, 255-field*2], axis=-1).astype(np.uint8)
    canvas = Image.fromarray(colors).convert('RGBA')
    curves = Image.new('RGBA', canvas.size)
    draw = ImageDraw.Draw(curves)
    for displacement in [0, 30, 65]:
        path = [(1110+1480*t, 1390-1130*np.sin(t*np.pi*.88)+displacement)
                for t in np.linspace(0, 1, 500)]
        draw.line(path, fill=(105, 164, 221, 24), width=2)
    canvas.alpha_composite(curves)

    # Each official product image appears once. Larger source photos lead the composition.
    # id, center x/y, max width/height, rotation; product geometry/colors are not repainted.
    layout = [
        ('allegro-01', 1155, 1230, 305, 390, 32),
        ('shadow-02', 1570, 1270, 260, 440, 8),
        ('unitree-03', 1400, 290, 240, 300, 24),
        ('unitree-04', 1790, 190, 235, 260, -5),
        ('unitree-05', 2330, 295, 270, 300, -40),
        ('wuji-06', 2600, 555, 250, 300, -72),
        ('wuji-07', 2140, 1310, 365, 390, -18),
        ('brainco-08', 1435, 660, 255, 290, 40),
        ('robotera-09', 2080, 490, 240, 310, -35),
        ('tesollo-10', 2560, 1100, 300, 380, -55),
        ('schunk-11', 1770, 510, 235, 320, 0),
        ('robotis-12', 1125, 735, 255, 300, 58),
        ('orca-13', 2550, 140, 190, 270, -90),
        ('dexrobot-14', 2415, 795, 260, 250, -45),
        ('oymotion-15', 1310, 980, 240, 280, 52),
        ('linkerbot-16', 1860, 1070, 290, 320, 20),
        ('sharpa-17', 2450, 1330, 270, 320, -25),
        ('barrett-18', 1100, 360, 270, 230, 28),
    ]
    assert {p['id'] for p in products} == {item[0] for item in layout}
    for product_id, cx, cy, max_w, max_h, angle in layout:
        frame = frames[product_id].copy()
        frame.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        frame = frame.rotate(angle, Image.Resampling.BICUBIC, expand=True)
        position = (int(cx-frame.width/2), int(cy-frame.height/2))
        assert position[0] >= 0 and position[1] >= 0
        assert position[0]+frame.width <= w and position[1]+frame.height <= h
        layer = Image.new('RGBA', canvas.size)
        layer.alpha_composite(frame, position)
        shadow = Image.new('RGBA', canvas.size, (64, 106, 151, 0))
        shadow.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v*.10)))
        canvas.alpha_composite(shadow)
        canvas.alpha_composite(layer)

    # A translucent object motif connects the hardware collection with grasp research.
    cx, cy, s = 1880, 785, 135
    cube = Image.new('RGBA', canvas.size)
    d = ImageDraw.Draw(cube)
    p = [(cx,cy-s),(cx+s,cy-s*.42),(cx+s,cy+s*.62),(cx,cy+s*1.18),
         (cx-s,cy+s*.62),(cx-s,cy-s*.42),(cx,cy+s*.14)]
    for ids, color in [([0,1,6,5],(232,244,255,210)),([1,2,3,6],(142,191,240,145)),
                       ([5,6,3,4],(189,224,253,155))]:
        d.polygon([p[i] for i in ids], fill=color)
    for a,b in [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0),(5,6),(1,6),(6,3)]:
        d.line([p[a],p[b]], fill=(102,159,217,150), width=2)
    canvas.alpha_composite(cube)

    text(canvas, (130,115), 'DEXTEROUSLAB / RESEARCH', 20, '#6887a7', MONO)
    text(canvas, (125,440), 'Dexterous', 154, '#17304e', BOLD)
    text(canvas, (125,608), 'Lab.', 185, '#17304e', BOLD)
    text(canvas, (138,770), 'Real hardware. Shared possibilities.', 35, '#5b7998')
    text(canvas, (138,830), 'A platform for dexterous interaction.', 31, '#718aa3')
    d = ImageDraw.Draw(canvas)
    d.line((140,940,228,940), fill='#83afd7', width=3)
    text(canvas, (138,1015), f'{len(products):02}', 82, '#244865')
    text(canvas, (285,1000), 'OFFICIAL PRODUCT IMAGES', 18, '#6988a7', MONO)
    text(canvas, (285,1036), f'{manifest["manufacturer_count"]} MANUFACTURERS', 18, '#6988a7', MONO)
    text(canvas, (138,1443), 'ASSETS / SIMULATION / GRASP RESEARCH', 17, '#7895b1', MONO)
    text(canvas, (2660,1517), 'ISAAC SIM + ISAAC LAB + ARENA', 18, '#7895b1', MONO, 'rm')
    canvas.convert('RGB').save(MEDIA / 'dexterouslab-official.png', optimize=True)

    # A separate named sheet makes source verification easy without cluttering the cover.
    gallery = Image.new('RGB', (2100, 1610), '#f8fbff')
    text(gallery, (65,68), 'Official product collection', 51, '#17304e', BOLD)
    text(gallery, (65,124), 'Manufacturer-published images / original product appearance', 24, '#718aa3')
    for index, product in enumerate(products):
        row, col = divmod(index, 6)
        cx, bottom = 180 + col*348, 530 + row*475
        frame = frames[product['id']].copy()
        frame.thumbnail((285, 330), Image.Resampling.LANCZOS)
        gallery.paste(frame, (int(cx-frame.width/2), int(bottom-frame.height)), frame)
        text(gallery, (cx,bottom+35), product['product_name'], 23, '#244865', BOLD, 'mm')
        text(gallery, (cx,bottom+72), product['manufacturer'], 18, '#7895b1', REGULAR, 'mm')
    gallery.save(DIRECTORY / 'collection.png', optimize=True)
    (DIRECTORY / 'composition.json').write_text(json.dumps({
        'generator': 'scripts/build_official_product_cover.py',
        'cover': 'docs/media/dexterouslab-official.png', 'size': [w,h],
        'image_count': len(products), 'manufacturer_count': manifest['manufacturer_count'],
        'operations': evidence, 'layout': layout,
        'notice': 'Native manufacturer imagery, no local hand renders or generated hands. Resizing/rotation/background compositing only. Decorative cube is not a simulation result.',
    }, indent=2) + '\n')
    print('COVER_CREATED', len(products), 'official product images', flush=True)


if __name__ == '__main__':
    main()
