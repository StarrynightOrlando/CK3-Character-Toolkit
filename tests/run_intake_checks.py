from pathlib import Path
import sys,tarfile,io
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bridge import core
from bridge.intake import inspect_source
fixtures=core.ROOT/'state/format_fixtures';results=[]
for suffix in ('blend','fbx','glb','gltf','obj','vrm'):
 output=inspect_source(fixtures/('fixture.'+suffix));r=core.load(output/'intake.json');assert r['imported'] and not r['ck3_ready'];assert r['meshes'];results.append({'format':suffix,'passed':True,'meshes':len(r['meshes']),'armatures':len(r['armatures']),'output':str(output)})
package=fixtures/'fixture.unitypackage'
with tarfile.open(package,'w:gz') as a:
 data=b'Assets/Models/fixture.fbx';member=tarfile.TarInfo('fixture-guid/pathname');member.size=len(data);a.addfile(member,io.BytesIO(data))
output=inspect_source(package);r=core.load(output/'intake.json');assert r['asset_paths']==['Assets/Models/fixture.fbx'] and not r['imported'];results.append({'format':'unitypackage_inventory','passed':True,'output':str(output)})
core.save(core.ROOT/'state/intake-acceptance.json',{'passed':True,'synthetic_fixtures':True,'real_vrm_metadata_verified':False,'checks':results})
print('INTAKE_CHECKS_PASSED',len(results))
