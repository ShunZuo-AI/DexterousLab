"""Sequential one-articulation, 100-step GPU validation of explicit asset IDs."""
import json
from pathlib import Path
import sys
import traceback
from dexterous_lab.assets.catalog import save_json
from dexterous_lab.assets.manager import AssetManager

DEFAULT_IDS = ['brainco/revo2/revo2_right_hand',
 'linkerbot/linkerhand_l20/right_linkerhand_l20_right',
 'sharpa/sharpa_wave_wave_01/right_sharpa_wave_right_sharpa_wave',
 'tesollo/dg5f/dg5f_right', 'psyonic/ability_hand/ability_hand_right_large',
 'schunk/svh/schunk_svh_hand_right', 'barrett/barrett_hand/bhand_model',
 'robotis/hx5/urdf_hx5_d20_right', 'dexrobot/dexhand021/dexhand021_right',
 'oymotion/rohand/urdf_rohand_right',
 'fourier/fourier_hand/dexterous_hand_fourier_hand_6dof_urdf_fourier_right_hand_6dof',
 'unitree/dex1_1/unspecified','unitree/dex2_5/right','unitree/dex5_1/right',
 'wuji/hand_v2/2_1_right','wuji/hand_v2/2_2_right']

def main():
 manager=AssetManager()
 destination=Path('docs/asset_aggregation')
 previous=destination/'expanded-simulation-results.json'
 rows=json.loads(previous.read_text()) if previous.exists() else []
 failed=False
 for aid in sys.argv[1:] or DEFAULT_IDS:
  row={'asset_id':aid,'steps_requested':100}
  try:
   row['conversion']=manager.convert(aid)
   row['validation']=manager.validate(aid,steps=100)
   row['passed']=True
  except Exception as exc:
   row.update(passed=False,error=str(exc))
   failed=True
  rows.append(row)
  print(json.dumps(row),flush=True)
  save_json(destination/'expanded-simulation-results.json',rows)
 return int(failed)

if __name__=='__main__':sys.exit(main())
