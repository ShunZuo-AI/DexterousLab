"""Fetch sparse source references without installing or executing vendor code."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PLAN = {
 'BrainCoTech/revo2_description': ['urdf','meshes'],
 'linker-bot/linkerhand-urdf': ['L20/right'],
 'sharpa-robotics/sharpa-urdf-usd-xml': ['wave_01/right_sharpa_wave'],
 'facebookresearch/spider': ['spider/assets/robots/xhand'],
 'tesollodelto/dg5f_ros2': ['dg5f_description'],
 'psyonicinc/ability-hand-api': ['URDF'],
 'dexsuite/dex-urdf': ['robots/hands/schunk_hand','robots/hands/barrett_hand','robots/hands/inspire_hand'],
 'whats-lab/dexterous-hand-urdf': ['dexhand_description/robotis_hx5_d20'],
 'orcahand/orcahand_description': ['v1/models'],
 'DexRobot/dexrobot_urdf': ['urdf','meshes'],
 'oymotion/rohand_urdf_ros1': ['urdf','meshes'],
 'FFTAI/Wiki-GRx-Models': ['Dexterous_hand/fourier_hand_6dof'],
 'shadow-robot/dx_common': ['dx_description'],
 'Roboparty/rp_dexhand': [],
 'ruka-hand/RUKA': [],
}

def run(repo):
 destination = ROOT/'research-repos'/repo.split('/')[-1]
 log = ROOT/'docs/asset_aggregation'/('prepare-'+repo.replace('/','-')+'.log')
 result = {'repository':repo,'checkout':str(destination)}
 try:
  with log.open('a') as stream:
   if not destination.exists():
    subprocess.run(['git','clone','--depth','1','--filter=blob:none','--sparse','https://github.com/'+repo+'.git',str(destination)],stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=180)
   elif not (destination/'.git').is_dir():
    raise ValueError('Existing directory is not a git checkout; preserve it')
   if PLAN[repo]:
    subprocess.run(['git','-C',str(destination),'sparse-checkout','add',*PLAN[repo]],stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=180)
   names=subprocess.check_output(['git','-C',str(destination),'ls-tree','--name-only','HEAD'],text=True).splitlines()
   evidence=[n for n in names if n.lower().startswith(('license','notice','readme'))]
   missing_evidence=[name for name in evidence if not (destination/name).exists()]
   if missing_evidence:
    subprocess.run(['git','-C',str(destination),'restore','--source=HEAD','--worktree','--ignore-skip-worktree-bits',*missing_evidence],stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=90)
   result.update(status='prepared',commit=subprocess.check_output(['git','-C',str(destination),'rev-parse','HEAD'],text=True).strip(),evidence_files=evidence)
 except Exception as exc: result.update(status='failed',error=str(exc))
 print(repo,result['status'],flush=True)
 return result

if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(run,PLAN))
 (ROOT/'docs/asset_aggregation/reference-preparation.json').write_text(json.dumps(results,indent=2)+'\n')
