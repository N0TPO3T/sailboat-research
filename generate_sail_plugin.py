# Generate an isolated sail-polar plugin; retain installed underwater implementation.
from pathlib import Path
R=Path(__file__).resolve().parent
original=R.parent/'workspace/src/Yara_OVE/yara_gazebo_plugins'
s=(original/'src/liftDragForces.cc').read_text();h=(original/'include/liftDragForces.hh').read_text()
water=s[s.index('  if (this->waterVelVec.Length() > 0.001)'):]
s=s.replace('LiftDragForces','MigrationSailPolar')
s=s.replace('#include "../include/liftDragForces.hh"','#include "sail_polar_plugin.hh"\n#include "../legacy_parameters.hh"\n#include <ros/ros.h>')
start=s.index('    if (this->coefIndex > 100)');end=s.index('    this->force_on_sail = this->lift + this->drag;',start)
s=s[:start]+'''    // Original cubic polar; Yara apparent wind, pressure and 3D directions retained.
    this->lift = this->q * legacy::sail_cl(this->atkangle) * this->liftDirection;
    this->drag = this->q * legacy::sail_cd(this->atkangle) * this->dragDirection;
'''+s[end:]
start=s.index('    double sign = 1.0;');end=s.index('    //->Force on sail:',start)
s=s[:start]+'''    const double sign = 1.0;
    this->baseLink->AddForceAtRelativePosition(this->force_on_sail, this->sailCP);
    // Preserve Yara keel compensation, driven by the applied sail force.
    sail_lateral_force = (this->force_on_sail.Dot(port) / (port.Length() * port.Length())) * port;

'''+s[end:]
marker='  ignition::math::Vector3d sail_lateral_force = ignition::math::Vector3d(0, 0, 0);'
assert s.count(marker)==1
s=s.replace(marker,marker+'''
  this->force_on_sail.Set(0,0,0);this->lift.Set(0,0,0);this->drag.Set(0,0,0);
  this->liftDirection.Set(0,0,0);this->dragDirection.Set(0,0,0);
  this->q=0;this->atkangle=0;this->alpha=0;
''')
marker='  if (this->waterVelVec.Length() > 0.001)'
telemetry='''  // Last force update of each policy second, before the corresponding observation.
  if (++this->diagnosticTicks % 100 == 0) {
    XmlRpc::XmlRpcValue d;
    d["model"]=this->modelName;d["source"]=std::string("legacy_polar");
    d["clock"]=this->world->SimTime().Double();d["attack_deg"]=this->atkangle;
    d["cl"]=legacy::sail_cl(this->atkangle);d["cd"]=legacy::sail_cd(this->atkangle);
    d["pressure"]=this->q;d["sail_area"]=this->sailArea;d["air_density"]=this->airRHO;
    for(auto key:{"wind_world","lift_world","drag_world","force_world","lift_direction_world","drag_direction_world"})d[key].setSize(3);
    for(int i=0;i<3;i++){
      d["wind_world"][i]=this->aparentWindVelVec[i];d["lift_world"][i]=this->lift[i];
      d["drag_world"][i]=this->drag[i];d["force_world"][i]=this->force_on_sail[i];
      d["lift_direction_world"][i]=this->liftDirection[i];d["drag_direction_world"][i]=this->dragDirection[i];
    }
    ros::param::set("/migration/sail_diagnostics",d);
  }

'''
s=s.replace(marker,telemetry+marker)
assert s[s.index(marker):]==water.replace('LiftDragForces','MigrationSailPolar'),'underwater code changed'
assert 'std::rand' not in s and '0.1 * this->force_on_sail' not in s and 'coefIndex > 100' not in s
h=h.replace('LiftDragForces','MigrationSailPolar').replace('_EBOAT_GAZEBO_LIFTDARG_PLUGIN_HH_','_MIGRATION_SAIL_POLAR_HH_').replace('_EBOAT_GAZEBO_LIFTDRAG_PLUGIN_HH_','_MIGRATION_SAIL_POLAR_HH_')
h=h.replace('protected: virtual void OnUpdate();','protected: virtual void OnUpdate();\n        protected: unsigned diagnosticTicks=0;')
(R/'build').mkdir(exist_ok=True)
(R/'build/sail_polar_plugin.cc').write_text(s);(R/'build/sail_polar_plugin.hh').write_text(h)
print('Generated isolated MigrationSailPolar; underwater source retained verbatim.')
