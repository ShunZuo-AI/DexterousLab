"""Build self-contained vector typography and icons for the research README."""

from html import escape
from pathlib import Path

from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as VectorPath
from matplotlib.textpath import TextPath


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/media/readme-style'
SERIF = '/usr/share/fonts/truetype/noto/NotoSerifDisplay-Italic.ttf'
SANS = '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'
CHINESE = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
INK = '#173d68'
BLUE = '#4d88c6'
MUTED = '#7893ae'
ICONS = {
    'overview': '<ellipse cx="12" cy="12" rx="10" ry="4"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)"/><circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none"/>',
    'quick-start': '<path d="M8 15c-1-6 3-11 12-12 0 9-5 13-12 12Z M8 10 4 11l-1 6 5-2 M13 16l-1 5 6-2 1-5 M7 17l-3 3 M9 19l-2 2"/><circle cx="15" cy="8" r="2"/>',
    'hand-assets': '<path d="M7 13V6a1.5 1.5 0 0 1 3 0v6-8a1.5 1.5 0 0 1 3 0v8-7a1.5 1.5 0 0 1 3 0v8-5a1.5 1.5 0 0 1 3 0v8c0 4-3 6-6 6h-2c-2 0-4-2-5-4l-3-5a1.5 1.5 0 0 1 2-2l2 2Z"/>',
    'experiments': '<path d="M9 3h6 M10 3v7l-6 9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2l-6-9V3 M7 15h10"/><circle cx="11" cy="17" r=".8"/><circle cx="14" cy="19" r=".6"/>',
    'architecture': '<path d="m3 7 9-5 9 5-9 5-9-5Z M3 12l9 5 9-5 M3 17l9 5 9-5"/>',
    'validation': '<path d="m12 2 8 3v6c0 5-4 9-8 11-4-2-8-6-8-11V5l8-3Z M8 12l3 3 5-6"/>',
    'documentation': '<path d="M12 6C8 3 4 3 2 4v15c4-1 7 0 10 2 3-2 6-3 10-2V4c-2-1-6-1-10 2v15 M5 8l4 1 M5 12l4 1 M15 9l4-1 M15 13l4-1"/>',
    'research': '<circle cx="12" cy="4" r="2.5"/><circle cx="4" cy="19" r="2.5"/><circle cx="20" cy="19" r="2.5"/><path d="m11 6-6 10 M13 6l6 10 M7 19h10"/>',
    'cube': '<path d="m12 2 9 5v10l-9 5-9-5V7l9-5Z M3 7l9 5 9-5 M12 12v10"/>',
}
SECTIONS = [
    ('overview', 'Overview', '项目概览', '01'),
    ('quick-start', 'Getting Started', '快速开始', '02'),
    ('hand-assets', 'The Hand Collection', '灵巧手资产', '03'),
    ('experiments', 'Experiments', '实验展示', '04'),
    ('architecture', 'Inside the Framework', '框架逻辑', '05'),
    ('research', 'Research in Progress', '算法与接口状态', '06'),
    ('validation', 'Reproducibility', '测试与可复现性', '07'),
    ('documentation', 'Explore the Docs', '文档中心', '08'),
]


def letters(value, x, baseline, size, font=SERIF, fill=INK, anchor='start'):
    vector = TextPath((0, 0), value, size=size, prop=FontProperties(fname=font))
    bounds = vector.get_extents()
    if anchor == 'middle':
        x -= (bounds.x0+bounds.x1)/2
    if anchor == 'end':
        x -= bounds.x1
    commands = []
    codes = {VectorPath.MOVETO: 'M', VectorPath.LINETO: 'L', VectorPath.CURVE3: 'Q', VectorPath.CURVE4: 'C'}
    for vertices, code in vector.iter_segments(curves=True, simplify=False):
        if code == VectorPath.CLOSEPOLY:
            commands.append('Z')
        elif code in codes:
            commands.append(codes[code]+' '.join(f'{coordinate:.2f}' for coordinate in vertices))
    return f'<path transform="translate({x:.2f} {baseline}) scale(1 -1)" fill="{fill}" d="{" ".join(commands)}"/>'


def icon(name, x, y, size=40, color=BLUE):
    return f'<g transform="translate({x} {y}) scale({size/24})" fill="none" stroke="{color}" color="{color}" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>'


def document(width, height, title, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">
<title id="title">{escape(title)}</title>
<defs>
  <linearGradient id="wash"><stop stop-color="#f0f7ff"/><stop offset="1" stop-color="#ffffff"/></linearGradient>
  <linearGradient id="ink"><stop stop-color="#143b69"/><stop offset="1" stop-color="#6ba8dd"/></linearGradient>
  <linearGradient id="rule"><stop stop-color="#91bce6"/><stop offset="1" stop-color="#eaf4ff"/></linearGradient>
</defs>
{body}
</svg>
'''


def save(name, width, height, title, body):
    (OUT/name).write_text(document(width,height,title,body))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for key, english, chinese, number in SECTIONS:
        body = '<rect x="0" y="0" width="1080" height="120" rx="15" fill="url(#wash)"/>'
        body += '<circle cx="53" cy="55" r="30" fill="#e4f0ff"/>'
        body += icon(key,33,35,40)
        body += letters(english,105,64,45)
        body += letters(chinese,107,99,23,CHINESE,MUTED)
        body += letters(number,1036,74,43,SERIF,'#a4c4e1',anchor='end')
        body += '<path d="M105 117H1040" stroke="url(#rule)"/>'
        save(key+'.svg',1080,120,english+' · '+chinese,body)
        small = '<rect x="1" y="1" width="178" height="46" rx="23" fill="#edf5ff" stroke="#d2e5f8"/>'
        small += icon(key,17,13,22)
        small += letters(chinese,52,31,17,CHINESE,INK)
        save('nav-'+key+'.svg',180,48,chinese,small)
        save('icon-'+key+'.svg',32,32,chinese,icon(key,3,3,26))

    body = '<rect width="1080" height="220" fill="url(#wash)"/>'
    body += '<path d="M140 126C245 185 830 185 950 58" stroke="#d3e8fc" stroke-width="1.3" fill="none"/>'
    body += letters('DexterousLab',540,121,108,SERIF,'url(#ink)',anchor='middle')
    body += letters('A shared workspace for dexterous manipulation research',540,174,22,SANS,MUTED,anchor='middle')
    body += '<path d="m99 74 4-12 4 12 12 4-12 4-4 12-4-12-12-4Z" fill="#a8cbed"/><path d="m969 151 3-9 3 9 9 3-9 3-3 9-3-9-9-3Z" fill="#b4d4f1"/>'
    save('wordmark.svg',1080,220,'DexterousLab — A shared workspace for dexterous manipulation research',body)

    for name,number,title in [('assets','22','Validated configurations'),('makers','17','Manufacturers / projects'),('hands','2','Tabletop embodiments'),('objects','3','Primitive object types')]:
        body = '<rect width="240" height="88" rx="12" fill="#f4f9ff"/>'
        body += letters(number,120,65,64,SERIF,'url(#ink)',anchor='middle')
        save('stat-'+name+'.svg',240,88,number+' '+title,body)

    body=''
    for index,(symbol,title,subtitle) in enumerate([
        ('hand-assets','Curate.','资产与配置'),('architecture','Simulate.','场景与物理'),('experiments','Understand.','观测与结果')]):
        x=index*360
        body+=f'<rect x="{x+5}" y="5" width="345" height="160" rx="15" fill="#f4f9ff" stroke="#dfecf9"/>'
        body+=icon(symbol,x+28,27,32)
        body+=letters(title,x+78,65,38)
        body+=letters(subtitle,x+29,112,23,CHINESE,MUTED)
        body+=f'<path d="M{x+29} 139H{x+315}" stroke="#d5e6f8"/>'
    save('pillars.svg',1080,172,'Curate · 资产与配置 / Simulate · 场景与物理 / Understand · 观测与结果',body)

    for key,title,chinese,number in [('check','Check the environment','检查环境','01'),('scene','Build a scene','运行桌面场景','02'),('grasp','Run an experiment','执行抓取尝试','03')]:
        body='<rect width="760" height="66" rx="10" fill="#f6faff"/>'
        body+=letters(number,23,46,31,SERIF,BLUE)
        body+=letters(title,83,40,30,SERIF,INK)
        body+=letters(chinese,734,42,20,CHINESE,MUTED,anchor='end')
        save('step-'+key+'.svg',760,66,title+' · '+chinese,body)

    body='<path d="M32 22H480 M600 22H1048" stroke="url(#rule)"/>'
    body+=icon('overview',526,8,28,'#82add5')
    body+=letters('From many hands to meaningful experiments.',540,94,43,SERIF,INK,anchor='middle')
    body+=letters('DexterousLab  /  Research Preview',540,137,18,SANS,MUTED,anchor='middle')
    save('footer.svg',1080,170,'From many hands to meaningful experiments. DexterousLab Research Preview.',body)
    print('Generated',len(list(OUT.glob('*.svg'))),'self-contained SVG assets.')


if __name__=='__main__':
    main()
