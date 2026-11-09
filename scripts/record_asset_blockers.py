"""Register confirmed additional formats and concrete remaining source blockers."""
import copy
import json
from pathlib import Path
import subprocess
from dexterous_lab.assets.catalog import AssetCatalog,save_json
from dexterous_lab.assets.manager import AssetManager

ROOT=Path(__file__).resolve().parents[1];c=AssetCatalog();m=AssetManager(c)

def register(aid,repo,checkout,path,package,license_expression,blocker):
 try:return c.get(aid)
 except ValueError:pass
 manufacturer,model,variant=aid.split('/')
 r={'category':'hands','asset_id':aid,'manufacturer':manufacturer,'model':model,'variant':variant,
    'source_repository':repo,'source_commit':subprocess.check_output(['git','-C',str(ROOT/'research-repos'/checkout),'rev-parse','HEAD'],text=True).strip(),
    'source_file_path':path,'local_raw_path':None,'local_processed_path':None,'isaaclab_asset_path':None,
    'license':{'status':'reviewed','expression':license_expression,'evidence_paths':['LICENSE']},
    'download_status':'not_downloaded','conversion_status':'blocked_format_adapter','simulation_status':'not_run',
    'blocking_reason':blocker,'reference_checkout':checkout,'source_package':package,'fetch_enabled':True,'notes':[]}
 return c.register(r)

r=register('ruka/ruka/hand_assembly','https://github.com/ruka-hand/RUKA','RUKA','assets/xml/hand_assembly.xml','assets/xml','MIT',
           'Source is MJCF with tendons/equality/controller semantics; MJCF-to-PhysX adapter is not implemented or validated')
m.fetch(r['asset_id'])
for name in ('qbhand','qbhand2m'):
 r=register('qb_robotics/'+name+'/default','https://bitbucket.org/qbrobotics/qbhand-ros','qbhand-ros',
            'qb_hand_description/urdf/'+name+'.urdf.xacro','qb_hand_description','BSD-3-Clause',
            'Requires xacro and ROS package substitutions; xacro is not installed in the shared environment')
 m.fetch(r['asset_id'])
for r in c.records():
 if r['manufacturer']=='shadow_robot' and r['model']=='dex_ee':
  c.update(r,conversion_status='blocked_xacro_dependency',blocking_reason='Requires xacro with dx_description ROS substitutions; xacro is not installed')
 elif r['manufacturer']=='inspire':
  c.update(r,blocking_reason='Concrete RH56DFX-2LR paths indexed, but per-model mesh license grant not confirmed; do not infer it from the parent project license')
 elif r['manufacturer']=='roboparty':
  manifest=ROOT/'research-repos/rp_dexhand/resources/resources-2026.10.05/manifest.json'
  data=json.loads(manifest.read_text());archives=[a for a in data['assets'] if a['category']=='models']
  c.update(r,download_status='blocked_license',source_release_models=archives,
           blocking_reason=data['redistribution_status']+' LICENSES.md does not grant model-use terms; source archives exist but are not fetched')
 elif r['manufacturer']=='seed_robotics':
  root=ROOT/'research-repos/ros_robothands'
  paths=subprocess.check_output(['git','-C',str(root),'ls-tree','-r','--name-only','HEAD'],text=True).splitlines()
  models=[p for p in paths if p.lower().endswith(('.urdf','.xacro','.usd','.usda','.stl','.dae'))]
  c.update(r,source_commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),
           source_repository='https://github.com/seedrobotics/ros_robothands',
           blocking_reason='Official linked repository is accessible; recursive tree contains '+str(len(models))+' URDF/Xacro/USD/STL/DAE files; driver code is not a hand model')
 elif r['manufacturer']=='qb_robotics' and r['model']=='unresolved':
  c.update(r,blocking_reason='GitHub candidate superseded by verified official Bitbucket source; see qb_robotics/qbhand/default and qbhand2m/default')
 elif r['simulation_status']=='failed':
  c.update(r,blocking_reason='Actual PhysX validation failed; retained logs at '+r.get('last_run',''))

save_json(ROOT/'docs/asset_aggregation/repository-rechecks.json',{
 'seed_robotics':{'commit':subprocess.check_output(['git','-C',str(ROOT/'research-repos/ros_robothands'),'rev-parse','HEAD'],text=True).strip(),'model_paths':models},
 'qb_robotics':{'commit':subprocess.check_output(['git','-C',str(ROOT/'research-repos/qbhand-ros'),'rev-parse','HEAD'],text=True).strip(),'url':'https://bitbucket.org/qbrobotics/qbhand-ros'},
 'roboparty':{'manifest_path':str(manifest),'archives':archives,'licensing_statement':data['redistribution_status']}})
