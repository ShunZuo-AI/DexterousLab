"""Explicitly approved second asset batch; preserve provenance and original files."""
import json
from pathlib import Path
from dexterous_lab.assets.catalog import AssetCatalog, save_json
from dexterous_lab.assets.manager import AssetManager
from dexterous_lab.assets.checks import inspect_urdf

ROOT=Path(__file__).resolve().parents[1]
# License contents were read from these exact commits before enabling retrieval.
PLAN={
 'brainco':('revo2_description','.', 'revo2_description','Apache-2.0',['LICENSE']),
 'linkerbot':('linkerhand-urdf','L20/right','','Apache-2.0',['LICENSE']),
 'sharpa':('sharpa-urdf-usd-xml','wave_01/right_sharpa_wave','','Apache-2.0',['LICENSE.txt','NOTICE.txt']),
 'robotera':('spider','spider/assets/robots/xhand','','LicenseRef-Meta-CC-BY-NC',['LICENSE']),
 'tesollo':('dg5f_ros2','dg5f_description','','BSD-3-Clause',['LICENSE']),
 'psyonic':('ability-hand-api','URDF','','MIT',['LICENSE']),
 'schunk':('dex-urdf','robots/hands/schunk_hand','','GPL-3.0',['LICENSE','robots/hands/schunk_hand/LICENSE']),
 'barrett':('dex-urdf','robots/hands/barrett_hand','','BSD-3-Clause',['LICENSE','robots/hands/barrett_hand/LICENSE']),
 'robotis':('dexterous-hand-urdf','dexhand_description/robotis_hx5_d20','','Apache-2.0',['dexhand_description/robotis_hx5_d20/LICENSE']),
 'orca':('orcahand_description','v1','','MIT',['LICENSE']),
 'dexrobot':('dexrobot_urdf','.','dexrobot_urdf','Apache-2.0',['LICENSE']),
 'oymotion':('rohand_urdf_ros1','.','rohand_urdf_ros1','MIT',['LICENSE']),
 'fourier':('Wiki-GRx-Models','Dexterous_hand/fourier_hand_6dof','','GPL-3.0',['LICENSE']),
 'shadow_robot':('dx_common','dx_description','','BSD-3-Clause',['LICENSE']),
}

def main():
 c=AssetCatalog();m=AssetManager(c);results=[]
 for r in c.records():
  vendor=r['manufacturer']
  if r['download_status'] in ('fetched','reference_recorded'): continue
  if vendor in ('unitree','wuji') and r.get('source_file_path'):
   r=c.update(r,fetch_enabled=True)
  elif vendor in PLAN and r.get('source_file_path'):
   checkout,package,prefix,expression,licenses=PLAN[vendor]
   if not r['source_repository'].endswith('/'+checkout): continue
   if not r['source_file_path'].startswith(package.rstrip('.') or ''): continue
   if not (ROOT/'research-repos'/checkout/r['source_file_path']).is_file(): continue
   r=c.update(r,fetch_enabled=True,reference_checkout=checkout,source_package=package,raw_prefix=prefix,
              license={'status':'reviewed','expression':expression,'evidence_paths':licenses,
                       'scope':'Separate third-party model assets, original notices retained; no relicensing',
                       'restrictions':['noncommercial only'] if vendor=='robotera' else []})
  else: continue
  row={'asset_id':r['asset_id']}
  try:
   fetched=m.fetch(r['asset_id']);row['fetch_status']=fetched['status'];r=c.get(r['asset_id']);d=c.directory(r)
   if Path(r['local_raw_path']).suffix=='.urdf':
    report=inspect_urdf(r['local_raw_path'],d/'raw');save_json(d/'static_validation.json',report)
    row.update(static_passed=report['passed'],failures=report['failures'])
    c.update(r,static_status='passed' if report['passed'] else 'failed')
   else: row['static_passed']=None
  except Exception as exc: row['error']=str(exc)
  results.append(row);print(json.dumps(row),flush=True)
 save_json(ROOT/'docs/asset_aggregation/expanded-fetch-results.json',results)

if __name__=='__main__':main()
