from environment import *
import hashlib,xml.etree.ElementTree as E,platform,subprocess
import torch,gymnasium,scipy
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=R/'frozen/checkpoints/obstacle_candidate/saclstm_s14obst_noise_0204_normalizer10800.pth'
stats=torch.load(p,map_location='cpu',weights_only=True)
names=['local_x','local_y','phi','local_psi','u','v','p','r','sail_actual','rudder_actual','distance_progress','local_x_progress','goal_x','goal_y','obstacle_1_distance','obstacle_1_bearing','obstacle_2_distance','obstacle_2_bearing']
units=['m','m','rad','rad','m/s','m/s','rad/s','rad/s','rad','rad','m','m','m','m','m','rad','m','rad']
text='# Frozen normalization and observation schema\n\nAll samples at reset or after the exact 1 s transition. Initial progress=0; only obstacle slots use missing=(0,0). Finite float32 input; no added clipping.\n\n|Index|Name|Unit|Mean|Std (before +1e-6)|\n|---|---|---|---|---|\n'
for i,name in enumerate(names):text+=f'|{i}|{name}|{units[i]}|{stats["mean"][i].item():.9g}|{stats["var"][i].sqrt().item():.9g}|\n'
(R/'NORMALIZATION.md').write_text(text)
e=MigrationEnv('original');root=E.parse(R/'boat.urdf').getroot()
links=[]
for link in root.findall('link'):
 inert=link.find('inertial')
 if inert is not None:links.append(dict(name=link.attrib['name'],mass=float(inert.find('mass').attrib['value']),origin=inert.find('origin').attrib if inert.find('origin') is not None else None,inertia=inert.find('inertia').attrib))
plugins=[dict(name=x.attrib,parameters={y.tag:y.text for y in x}) for x in root.iter('plugin')]
joints=[dict(name=x.attrib,axis=x.find('axis').attrib if x.find('axis') is not None else None,origin=x.find('origin').attrib if x.find('origin') is not None else None,limit=x.find('limit').attrib if x.find('limit') is not None else None) for x in root.findall('joint')]
data=dict(legacy_parameters=e.env.par,yara_links=links,yara_total_mass=sum(x['mass'] for x in links),yara_plugins=plugins,yara_joints=joints,legacy_sail_rate=e.env.max_sail_rate,legacy_rudder_rate=e.env.max_rudder_rate,native_yara_cable_rate=.5,native_yara_rudder_rate=.4)
(R/'PHYSICS_PARAMETERS.json').write_text(json.dumps(data,indent=2))
ident=dict(host_python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,scipy=scipy.__version__,gymnasium=gymnasium.__version__,docker_image=subprocess.check_output(['docker','image','inspect','hs-yara:noetic-visual','--format','{{.Id}}'],text=True).strip(),yara_source=(R.parent/'SOURCE_COMMIT').read_text().strip())
(R/'VERSIONS.json').write_text(json.dumps(ident,indent=2))
assets={str(p.relative_to(R)):sha(p) for p in (R/'frozen/checkpoints/obstacle_candidate').glob('*.pth')}
(R/'ASSET_HASHES.json').write_text(json.dumps(assets,indent=2));e.close();print(assets)
