#include <gazebo/gazebo.hh>
#include <gazebo/physics/physics.hh>
#include <ros/ros.h>
#include <std_srvs/Trigger.h>
#include <thread>
#include <sstream>
#include <iomanip>
#include <cmath>
#include <set>
#include <gazebo/physics/ContactManager.hh>
#include <gazebo/physics/Contact.hh>
#include "legacy_dynamics.hh"
namespace gazebo {
class MigrationStep: public WorldPlugin {
 physics::WorldPtr w; physics::ModelPtr m; physics::JointPtr sail,rudder;
 event::ConnectionPtr update, afterUpdate;
 std::set<std::pair<std::string,std::string>> contactPairs; unsigned contactPoints=0; double contactDepth=0; std::unique_ptr<ros::NodeHandle> n;
 std::unique_ptr<ros::AsyncSpinner> spinner; ros::ServiceServer service;
 double cable=0, rudderTarget=0, sailTarget=0, sailStart=0, rudderStart=0;
 std::string actuatorMode="native", physicsMode="native"; int controlTick=0;
 legacy::State legacyState{}; double legacySail=0,legacyRudder=0,legacyDs=0,legacyDr=0,legacyWx=0,legacyWy=0;
 public: void Load(physics::WorldPtr world,sdf::ElementPtr) {
 w=world; n.reset(new ros::NodeHandle("migration"));
 service=n->advertiseService("step",&MigrationStep::step,this);
 update=event::Events::ConnectWorldUpdateBegin(std::bind(&MigrationStep::tick,this));
 w->Physics()->GetContactManager()->SetNeverDropContacts(true);
 afterUpdate=event::Events::ConnectWorldUpdateEnd(std::bind(&MigrationStep::contacts,this));
 spinner.reset(new ros::AsyncSpinner(1)); spinner->start();
 }
 void contacts() {
 if(!m)return;
 auto manager=w->Physics()->GetContactManager();const auto &entries=manager->GetContacts();
 const std::string prefix=m->GetScopedName()+"::";
 for(unsigned i=0;i<manager->GetContactCount();++i){
  auto c=entries[i];std::string a=c->collision1->GetScopedName(),b=c->collision2->GetScopedName();
  bool ownA=a.compare(0,prefix.size(),prefix)==0,ownB=b.compare(0,prefix.size(),prefix)==0;
  if(ownA==ownB)continue;
  contactPairs.insert({a,b});contactPoints+=c->count;
  for(int j=0;j<c->count;j++)contactDepth=std::max(contactDepth,c->depths[j]);
 }
 }
 void tick() {
 if(!m || !sail || !rudder) return;
 if(physicsMode=="legacy4dof") {
  const double dt=w->Physics()->GetMaxStepSize(),t=controlTick*dt;
  legacyState=legacy::rk4(legacyState,t,dt,legacySail,legacyRudder,legacyDs,legacyDr,legacyWx,legacyWy);
  ++controlTick;
  if(controlTick==100){legacyState[3]=legacy::wrap(legacyState[3]);for(auto &v:legacyState)v=static_cast<float>(v);}
  m->SetWorldPose(ignition::math::Pose3d(legacyState[0],legacyState[1],0,-legacyState[2],0,legacyState[3]));
  double sa=-(legacySail+controlTick*dt*legacyDs),ra=-(legacyRudder+controlTick*dt*legacyDr);
  sail->SetUpperLimit(0,sa);sail->SetLowerLimit(0,sa);rudder->SetUpperLimit(0,ra);rudder->SetLowerLimit(0,ra);
  sail->SetPosition(0,sa,true);rudder->SetPosition(0,ra,true);
  return;
 }
 if(m->IsStatic())return;
 if(actuatorMode=="signed") {
  // Prescribed-angle actuator, matching the inherited 1 s linear rate-limited motion.
  const double rate=M_PI/18, dt=w->Physics()->GetMaxStepSize();
  double fraction=std::min(1.,(++controlTick)*dt);
  auto advance=[&](double initial,double target){return initial+fraction*std::max(-rate,std::min(rate,target-initial));};
  double sp=advance(sailStart,sailTarget), rp=advance(rudderStart,rudderTarget);
  sail->SetUpperLimit(0,sp);sail->SetLowerLimit(0,sp);sail->SetPosition(0,sp,true);
  rudder->SetUpperLimit(0,rp);rudder->SetLowerLimit(0,rp);rudder->SetPosition(0,rp,true);
 } else {
 // Native Yara cable and rudder laws, synchronous target assignment.
 double sov=.5*w->Physics()->GetMaxStepSize();
 double upper=sail->UpperLimit(0);
 if(cable>upper+sov) {sail->SetUpperLimit(0,upper+sov);sail->SetLowerLimit(0,-upper-sov);}
 else if(cable<upper-sov) {sail->SetUpperLimit(0,upper-sov);sail->SetLowerLimit(0,-upper+sov);}
 double error=rudder->Position(0)-rudderTarget, a=std::abs(error);
 rudder->SetParam("fmax",0,100.);
 double vel=a<1e-4?0.:(a>.4*w->Physics()->GetMaxStepSize()?.4:a);
 rudder->SetParam("vel",0,error<0?vel:-vel);
 }
 }
 bool step(std_srvs::Trigger::Request&,std_srvs::Trigger::Response& out) {
 try {
 w->SetPaused(true);w->Physics()->SetRealTimeUpdateRate(0);
 std::string modelName;n->param<std::string>("model",modelName,"eboat_1");m=w->ModelByName(modelName);
 if(!m) {out.success=false;out.message="boat missing";return true;}
  sail=m->GetJoint("boom_joint"); rudder=m->GetJoint("rudder_joint");
 bool reset=false;int count=100;
 n->param("reset",reset,false);n->param("count",count,100);
 n->param<std::string>("actuator_mode",actuatorMode,"native");
 n->param<std::string>("physics_mode",physicsMode,"native");
 if(physicsMode!="native" && physicsMode!="legacy4dof")throw std::runtime_error("physics mode");
 n->param("sail_target",sailTarget,0.);
 if(actuatorMode!="native" && actuatorMode!="signed")throw std::runtime_error("actuator mode");
 n->param("cable",cable,0.);n->param("rudder",rudderTarget,0.);
 const double rudderLimit=(physicsMode=="native" && actuatorMode=="native")?M_PI/3:M_PI/6;
 if(count<0 || count>100 || cable<0 || cable>M_PI/2+1e-8 || std::abs(rudderTarget)>rudderLimit+1e-8) throw std::runtime_error("invalid controls");
 double wx=0,wy=8;n->param("wx",wx,0.);n->param("wy",wy,8.);
 w->Wind().SetLinearVel(ignition::math::Vector3d(wx,wy,0));
 if(reset) {
 sail->SetUpperLimit(0,0);sail->SetLowerLimit(0,0);
 sail->SetPosition(0,0);rudder->SetPosition(0,0);sail->SetVelocity(0,0);rudder->SetVelocity(0,0);
 }
 if(reset && physicsMode=="native") {
  std::vector<double> twist;n->getParam("initial_body_twist",twist);
  if(twist.size()!=6)throw std::runtime_error("initial_body_twist");
  auto base=m->GetLink("base_link");const auto pose=base->WorldPose();
  auto velocity=pose.Rot().RotateVector(ignition::math::Vector3d(twist[0],twist[1],twist[2]));
  auto omega=pose.Rot().RotateVector(ignition::math::Vector3d(twist[3],twist[4],twist[5]));
  // SetLinearVel sets CoG velocity, while RelativeLinearVel reads link-origin velocity.
  // Initialize every link as one rigid body, including the angular-velocity lever arm.
  for(auto link:m->GetLinks()){
   link->SetAngularVel(omega);
   link->SetLinearVel(velocity+omega.Cross(link->WorldCoGPose().Pos()-pose.Pos()));
  }
 }
 if(physicsMode=="legacy4dof") {
  if(actuatorMode!="signed")throw std::runtime_error("legacy4dof requires signed actuator");
  if(reset){std::vector<double> initial;n->getParam("legacy_initial",initial);if(initial.size()!=10)throw std::runtime_error("legacy_initial");for(int i=0;i<8;i++)legacyState[i]=initial[i];legacySail=initial[8];legacyRudder=initial[9];}
  else {legacySail=-sail->Position(0);legacyRudder=-rudder->Position(0);}
  legacyDs=std::max(-M_PI/18,std::min(M_PI/18,-sailTarget-legacySail));
  legacyDr=std::max(-M_PI/18,std::min(M_PI/18,-rudderTarget-legacyRudder));legacyWx=wx;legacyWy=wy;
  m->SetStatic(false);
  // Gazebo 11 ODELink::SetKinematic(true) toggles an already-kinematic body.
  // Query first so this operation is idempotent across policy steps.
  for(auto link:m->GetLinks()){if(!link->GetKinematic())link->SetKinematic(true);link->SetGravityMode(false);}
  // Kinematic links keep valid articulated joint feedback across repeated resets.
  // The custom 4DOF integrator owns motion; native force/contact response is disabled.
 }
 sailStart=sail->Position(0);rudderStart=rudder->Position(0);controlTick=0;
 contactPairs.clear();contactPoints=0;contactDepth=0;
 double start=w->SimTime().Double();
 if(count) w->Step(count);
 if(physicsMode=="legacy4dof") {
  auto desired=ignition::math::Pose3d(legacyState[0],legacyState[1],0,-legacyState[2],0,legacyState[3]);
  m->SetLinkWorldPose(desired,m->GetLink("base_link"));
 }
 auto b=m->GetLink("base_link");auto pose=b->WorldPose(); auto e=pose.Rot().Euler();
 auto v=b->RelativeLinearVel();auto a=b->RelativeAngularVel();
 if(physicsMode=="legacy4dof"){v.Set(legacyState[4],legacyState[5],0);a.Set(-legacyState[6],0,legacyState[7]);}
 double pd=a.X()+std::sin(e.X())*std::tan(e.Y())*a.Y()+std::cos(e.X())*std::tan(e.Y())*a.Z();
 if(physicsMode=="legacy4dof")pd=-legacyState[6];
 double rd=(std::sin(e.X())*a.Y()+std::cos(e.X())*a.Z())/std::cos(e.Y());
 std::ostringstream s;s<<std::setprecision(17);
 std::ostringstream contactJson;contactJson<<"[";bool first=true;
 for(const auto &pair:contactPairs){if(!first)contactJson<<",";first=false;contactJson<<"[\""<<pair.first<<"\",\""<<pair.second<<"\"]";}contactJson<<"]";
 s<<"{\"clock\":"<<w->SimTime().Double()<<",\"dt\":"<<w->SimTime().Double()-start
 <<",\"raw\":["<<pose.Pos().X()<<","<<pose.Pos().Y()<<","<<e.X()<<","<<e.Z()<<","<<v.X()<<","<<v.Y()<<","<<pd<<","<<a.Z()<<","<<sail->Position(0)<<","<<rudder->Position(0)<<",0,0,0,0]"
 <<",\"pose6\":["<<pose.Pos().X()<<","<<pose.Pos().Y()<<","<<pose.Pos().Z()<<","<<e.X()<<","<<e.Y()<<","<<e.Z()<<"]"
 <<",\"body_twist6\":["<<v.X()<<","<<v.Y()<<","<<v.Z()<<","<<a.X()<<","<<a.Y()<<","<<a.Z()<<"]"
 <<",\"euler_rates\":["<<pd<<","<<std::cos(e.X())*a.Y()-std::sin(e.X())*a.Z()<<","<<rd<<"]"
 <<",\"body_static\":"<<(m->IsStatic()?"true":"false")<<",\"body_kinematic\":"<<(b->GetKinematic()?"true":"false")
 <<",\"contact_points\":"<<contactPoints<<",\"contact_max_depth\":"<<contactDepth<<",\"contact_pairs\":"<<contactJson.str()
 <<",\"z\":"<<pose.Pos().Z()<<",\"pitch\":"<<e.Y()<<",\"cable_actual\":"<<sail->UpperLimit(0)
 <<",\"model_x\":"<<m->WorldPose().Pos().X()<<",\"model_y\":"<<m->WorldPose().Pos().Y()
 <<",\"physics_mode\":\""<<physicsMode<<"\""
 <<",\"actuator_mode\":\""<<actuatorMode<<"\""
 <<",\"cable_command\":"<<cable<<",\"rudder_command\":"<<rudderTarget
 <<",\"motor_command\":0,\"motor_applied_thrust\":0,\"motor_plugin_present\":false}";
 out.success=true;out.message=s.str();
 }catch(const std::exception&e){out.success=false;out.message=e.what();}return true;
 }
}; GZ_REGISTER_WORLD_PLUGIN(MigrationStep)
}
