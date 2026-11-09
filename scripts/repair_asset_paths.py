"""Record explicit source path corrections without altering upstream URDF or meshes."""
from pathlib import Path
import xml.etree.ElementTree as ET
from dexterous_lab.assets.catalog import AssetCatalog,save_json
from dexterous_lab.assets.manager import AssetManager
from dexterous_lab.assets.checks import inspect_urdf

c=AssetCatalog();m=AssetManager(c)
for r in c.records():
 if r['manufacturer']=='orca' and r['source_file_path'].startswith('v1/'):
  m.fetch(r['asset_id']);r=c.get(r['asset_id'])
 if r['manufacturer'] not in ('orca','robotera') or not r.get('local_raw_path'):continue
 d=c.directory(r);source=Path(r['local_raw_path']);tree=ET.parse(source);aliases={}
 for element in tree.findall('.//mesh'):
  original=element.get('filename')
  if r['manufacturer']=='robotera': candidate=source.parent/'assets'/Path(original).name
  else: candidate=d/'raw'/original.split('package://orcahand_description/',1)[1]
  if not candidate.is_file():raise ValueError(f'Missing exact source mesh: {candidate}')
  aliases[original]=str(candidate.relative_to(d/'raw'))
 r=c.update(r,mesh_aliases=aliases,path_adaptation='Explicit URDF mesh-reference correction; source URDF/mesh bytes unchanged')
 report=inspect_urdf(source,d/'raw',aliases);save_json(d/'static_validation.json',report)
 c.update(r,static_status='passed' if report['passed'] else 'failed')
 print(r['asset_id'],report['passed'],report['failures'],flush=True)
