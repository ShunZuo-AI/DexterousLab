"""Compose official product images with the user's ice-blue spatial reference style."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from build_official_product_cover import ROOT, MEDIA, DIRECTORY, cutout


WIDTH, HEIGHT = 3000, 1800
REGULAR = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
BOLD = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
ITALIC = '/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf'


def text(image, point, value, size, color, face=REGULAR, anchor='mm'):
    ImageDraw.Draw(image).text(point, value, fill=color,
        font=ImageFont.truetype(face, size), anchor=anchor)


def bloom(image, position, radius, color, opacity):
    layer = Image.new('RGBA', image.size)
    x,y = position
    ImageDraw.Draw(layer).ellipse((x-radius,y-radius,x+radius,y+radius), fill=(*color,opacity))
    soft = Image.new('RGBA',image.size,(*color,0))
    soft.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(radius*.55)))
    image.alpha_composite(soft)


def ribbon(image, cy, phase, front=False):
    """Draw a translucent ribbon around an inclined spatial ellipse."""
    layer = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(layer)
    start, end = (0,math.pi) if front else (math.pi,2*math.pi)
    upper,lower = [],[]
    for t in np.linspace(start,end,380):
        x = 1500+1460*math.cos(t)
        y = cy+190*math.sin(t)+.09*(x-1500)+38*math.sin(2*t+phase)
        width = 24+20*(1+math.sin(t))/2
        upper.append((x,y-width))
        lower.append((x+4,y+width))
    draw.polygon(upper+lower[::-1],fill=(156,206,252,26 if front else 32))
    draw.line(upper,fill=(255,255,255,205),width=3)
    draw.line(lower,fill=(119,180,238,95),width=2)
    inner = [(a[0],a[1]+10) for a in upper]
    draw.line(inner,fill=(224,244,255,165),width=2)
    glow = Image.new('RGBA',image.size,(213,238,255,0))
    glow.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(12)).point(lambda v:int(v*.25)))
    image.alpha_composite(glow)
    image.alpha_composite(layer)


def place(image, product, frame, center, max_size, angle, shadow_strength=.13):
    frame = frame.copy()
    frame.thumbnail(max_size,Image.Resampling.LANCZOS)
    frame = frame.rotate(angle,Image.Resampling.BICUBIC,expand=True)
    x,y = int(center[0]-frame.width/2),int(center[1]-frame.height/2)
    layer = Image.new('RGBA',image.size)
    layer.alpha_composite(frame,(x,y))
    shadow = Image.new('RGBA',image.size,(53,100,153,0))
    shadow.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(22)).point(lambda v:int(v*shadow_strength)))
    image.alpha_composite(shadow)
    image.alpha_composite(layer)
    return {'product_id':product['id'],'center_px':list(center), 'max_size':list(max_size),
            'angle_degrees':angle,'render_bounds':[x,y,x+frame.width,y+frame.height]}


def glass_cube(image, center, size):
    x,y = center
    pts=[(x,y-size),(x+size,y-size*.4),(x+size,y+size*.55),
         (x,y+size*1.1),(x-size,y+size*.55),(x-size,y-size*.4),(x,y+size*.1)]
    layer=Image.new('RGBA',image.size);d=ImageDraw.Draw(layer)
    for ids,color in [([0,1,6,5],(249,254,255,95)),([1,2,3,6],(126,188,248,35)),([5,6,3,4],(183,225,255,60))]:
        d.polygon([pts[i] for i in ids],fill=color)
    for a,b in [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0),(5,6),(1,6),(6,3)]:
        d.line([pts[a],pts[b]],fill=(255,255,255,215),width=3)
    image.alpha_composite(layer)


def panel(image, screenshot, origin, size):
    """Use a genuine experiment frame inside a subtle, decorative glass viewport."""
    x,y = origin;w,h = size
    layer = Image.new('RGBA',image.size)
    d=ImageDraw.Draw(layer)
    d.rounded_rectangle((x,y,x+w,y+h),radius=14,fill=(221,240,255,70),outline=(255,255,255,205),width=2)
    frame=Image.open(screenshot).convert('RGBA');frame.thumbnail((w-24,h-42),Image.Resampling.LANCZOS)
    frame.putalpha(105)
    layer.alpha_composite(frame,(x+12,y+30))
    d=ImageDraw.Draw(layer)
    for offset in [18,31,44]:d.ellipse((x+offset,y+12,x+offset+5,y+17),fill=(255,255,255,220))
    image.alpha_composite(layer)


def main():
    manifest=json.loads((DIRECTORY/'sources.json').read_text())
    products={p['id']:p for p in manifest['products']}
    frames={}
    for product_id,product in products.items():frames[product_id]=cutout(product)[0]
    yy,xx=np.mgrid[0:HEIGHT,0:WIDTH]
    blue=np.exp(-(((xx-1640)/1550)**2+((yy-1040)/1250)**2)*1.2)
    white=np.exp(-(((xx-1350)/1000)**2+((yy-240)/380)**2)*1.8)
    rgb=np.stack([248-blue*33+white*6,252-blue*20+white*3,255-blue*3],axis=-1)
    canvas=Image.fromarray(np.clip(rgb,0,255).astype(np.uint8)).convert('RGBA')
    bloom(canvas,(360,460),450,(255,255,255),95)
    bloom(canvas,(2310,650),550,(244,251,255),115)
    bloom(canvas,(1440,1430),570,(190,222,251),35)
    # Sweeping light establishes the depth and motion of the supplied reference.
    beams=Image.new('RGBA',canvas.size);d=ImageDraw.Draw(beams)
    d.polygon([(0,370),(0,415),(3000,1370),(3000,1250)],fill=(255,255,255,70))
    d.polygon([(0,1420),(0,1510),(3000,505),(3000,470)],fill=(255,255,255,90))
    soft_beams=Image.new('RGBA',canvas.size,(255,255,255,0))
    soft_beams.putalpha(beams.getchannel('A').filter(ImageFilter.GaussianBlur(12)))
    canvas.alpha_composite(soft_beams)
    for cy,phase in [(680,0),(1100,1),(1500,2)]:ribbon(canvas,cy,phase)
    panel(canvas,MEDIA/'allegro-tabletop.jpg',(2090,665),(380,225))
    panel(canvas,MEDIA/'shadow-tabletop.jpg',(485,1260),(350,210))

    # One full-size central product and a surrounding ecosystem; every photo is used once.
    # Smaller photographs remain upright enough to preserve recognizable manufacturer shapes.
    layout=[
        ('shadow-02',(385,380),(205,340),-22,(245,200)),
        ('allegro-01',(190,765),(240,280),-16,(185,955)),
        ('unitree-03',(695,495),(230,280),18,(690,665)),
        ('barrett-18',(840,850),(255,230),-22,(820,1010)),
        ('robotis-12',(440,1130),(225,275),-20,(400,1320)),
        ('oymotion-15',(160,1430),(205,270),-12,(170,1610)),
        ('brainco-08',(790,1460),(235,300),-22,(790,1650)),
        ('unitree-04',(1030,565),(175,210),16,(1030,710)),
        ('orca-13',(2690,385),(150,260),20,(2710,200)),
        ('sharpa-17',(2860,755),(215,275),22,(2840,950)),
        ('wuji-06',(2365,435),(230,300),22,(2365,245)),
        ('wuji-07',(2115,1020),(255,300),28,(2130,1220)),
        ('robotera-09',(2720,1130),(235,295),18,(2715,1320)),
        ('linkerbot-16',(2450,1460),(225,300),20,(2450,1660)),
        ('schunk-11',(2060,1520),(170,275),18,(2070,1710)),
        ('dexrobot-14',(2860,1490),(200,225),18,(2810,1650)),
        ('unitree-05',(2045,515),(220,245),-18,(2050,680)),
    ]
    placements=[]
    for product_id,center,max_size,angle,label_point in layout:
        product=products[product_id]
        placements.append(place(canvas,product,frames[product_id],center,max_size,angle))

    # Central official Tesollo photograph, dramatically larger than the supporting hands.
    hero='tesollo-10'
    placements.append(place(canvas,products[hero],frames[hero],(1500,1150),(890,1170),-24,.10))
    # Light ribbons cross only the wrist/base to keep the product's fingers readable.
    for cy,phase in [(665,0),(1495,2)]:ribbon(canvas,cy,phase,front=True)
    glass_cube(canvas,(995,1180),48)
    glass_cube(canvas,(2260,1350),37)
    glass_cube(canvas,(200,1740),70)
    glass_cube(canvas,(2790,1720),75)
    bloom(canvas,(1480,1620),280,(255,255,255),140)
    for product_id,center,max_size,angle,label_point in layout:
        text(canvas,label_point,products[product_id]['manufacturer'],25,'#193d69',BOLD)
    text(canvas,(1480,1710),'TESOLLO DG-5F-M',22,'#41688e',BOLD)

    # A single brand line follows the reference's strong, italic navy wordmark.
    title=Image.new('RGBA',canvas.size)
    text(title,(1500,135),'DexterousLab',160,'#07346b',ITALIC)
    halo=Image.new('RGBA',canvas.size,(255,255,255,0))
    halo.putalpha(title.getchannel('A').filter(ImageFilter.GaussianBlur(12)).point(lambda v:int(v*.8)))
    canvas.alpha_composite(halo);canvas.alpha_composite(title)
    text(canvas,(1500,260),'A shared platform for dexterous manipulation research',38,'#496c98',REGULAR)
    features=[('Multi-hand assets',1000),('Isaac Lab simulation',1430),('Traceable experiments',1885)]
    for label,x in features:
        text(canvas,(x,355),label,27,'#214a79',REGULAR)
    d=ImageDraw.Draw(canvas)
    # Small architectural glyphs echo the reference's restrained feature strip.
    ink='#214a79'
    d.line([(845,344),(862,334),(879,344),(862,355),(845,344),(845,365),(862,376),(879,365),(879,344)],fill=ink,width=2)
    d.line([(862,355),(862,376)],fill=ink,width=2)
    for oy in [0,9,18]:d.line([(1232,341+oy),(1250,332+oy),(1268,341+oy),(1250,351+oy),(1232,341+oy)],fill=ink,width=2)
    d.line([(1694,338),(1679,368),(1709,368),(1694,338)],fill=ink,width=2)
    for x,y in [(1694,338),(1679,368),(1709,368)]:d.ellipse((x-4,y-4,x+4,y+4),fill='#eef7ff',outline=ink,width=2)
    d.line((1213,336,1213,373),fill=(144,180,216,160),width=1)
    d.line((1660,336,1660,373),fill=(144,180,216,160),width=1)
    # Minimal, truthful image attribution lives at the edge; detailed sources stay in docs.
    text(canvas,(84,1760),'OFFICIAL PRODUCT IMAGERY  /  18 PRODUCTS · 15 MANUFACTURERS',17,'#537aa0',REGULAR,'lm')
    text(canvas,(2916,1760),'ISAAC SIM  /  ISAAC LAB  /  ARENA',17,'#537aa0',REGULAR,'rm')
    path=MEDIA/'dexterouslab-reference-style.png'
    canvas.convert('RGB').save(path,optimize=True)
    reference=ROOT/'901254c4-a89b-47dc-847e-b23e71e66e24.png'
    (DIRECTORY/'reference-style-composition.json').write_text(json.dumps({
        'generator':'scripts/build_reference_style_cover.py',
        'cover':str(path.relative_to(ROOT)),'size':[WIDTH,HEIGHT],
        'style_reference':str(reference.relative_to(ROOT)),
        'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
        'source_manifest':'docs/media/official-products/sources.json',
        'design':'Central large official Tesollo product, 17 supporting official product images, pale-blue glass ribbons, white-blue studio atmosphere and italic navy wordmark.',
        'placements':placements,
        'hero_product':hero,
        'notice':'User reference informs composition only; no reference brand identities or unsupported capability claims are copied. Actual source RGB preserved. Decorative ribbons/cubes are artwork; translucent panels contain real failed-trial close-phase screenshots.',
    },indent=2)+'\n')
    print('CREATED',path,flush=True)


if __name__=='__main__':
    main()
