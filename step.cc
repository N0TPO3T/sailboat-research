#include <gazebo/gazebo.hh>
#include <gazebo/physics/physics.hh>
#include <ros/ros.h>
#include <std_srvs/Trigger.h>
#include <thread>
#include <sstream>
#include <iomanip>
#include <cmath>
namespace gazebo {
class MigrationStep: public WorldPlugin {
 physics::WorldPtr w; physics::ModelPtr m; physics::JointPtr sail,rudder;
 event::ConnectionPtr update; std::unique_ptr<ros::NodeHandle> n;
 std::unique_ptr<ros::AsyncSpinner> spinner; ros::ServiceServer service;
 double cable=0, rudderTarget=0, sailTarget=0, sailStart=0, rudderStart=0;
 std::string actuatorMode="native"; int controlTick=0;
 public: void Load(physics::WorldPtr world,sdf::ElementPtr) {
 w=world; n.reset(new ros::NodeHandle("migration"));
 service=n->advertiseService("step",&MigrationStep::step,this);
 update=event::Events::ConnectWorldUpdateBegin(std::bind(&MigrationStep::tick,this));
 spinner.reset(new ros::AsyncSpinner(1)); spinner->start();
 }
 void tick() {
 if(!m || !sail || !rudder || m->IsStatic()) return;
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
 n->param("sail_target",sailTarget,0.);
 if(actuatorMode!="native" && actuatorMode!="signed")throw std::runtime_error("actuator mode");
 n->param("cable",cable,0.);n->param("rudder",rudderTarget,0.);
 if(count<0 || count>100 || cable<0 || cable>M_PI/2+1e-8 || std::abs(rudderTarget)>M_PI/6+1e-8) throw std::runtime_error("invalid controls");
 double wx=0,wy=8;n->param("wx",wx,0.);n->param("wy",wy,8.);
 w->Wind().SetLinearVel(ignition::math::Vector3d(wx,wy,0));
 if(reset) {
 sail->SetUpperLimit(0,0);sail->SetLowerLimit(0,0);
 sail->SetPosition(0,0);rudder->SetPosition(0,0);sail->SetVelocity(0,0);rudder->SetVelocity(0,0);
 }
 sailStart=sail->Position(0);rudderStart=rudder->Position(0);controlTick=0;
 double start=w->SimTime().Double();
 if(count) w->Step(count);
 auto b=m->GetLink("base_link");auto pose=b->WorldPose(); auto e=pose.Rot().Euler();
 auto v=b->RelativeLinearVel();auto a=b->RelativeAngularVel();
 double pd=a.X()+std::sin(e.X())*std::tan(e.Y())*a.Y()+std::cos(e.X())*std::tan(e.Y())*a.Z();
 double rd=(std::sin(e.X())*a.Y()+std::cos(e.X())*a.Z())/std::cos(e.Y());
 std::ostringstream s;s<<std::setprecision(17);
 s<<"{\"clock\":"<<w->SimTime().Double()<<",\"dt\":"<<w->SimTime().Double()-start
 <<",\"raw\":["<<pose.Pos().X()<<","<<pose.Pos().Y()<<","<<e.X()<<","<<e.Z()<<","<<v.X()<<","<<v.Y()<<","<<pd<<","<<a.Z()<<","<<sail->Position(0)<<","<<rudder->Position(0)<<",0,0,0,0]"
 <<",\"z\":"<<pose.Pos().Z()<<",\"pitch\":"<<e.Y()<<",\"cable_actual\":"<<sail->UpperLimit(0)
 <<",\"actuator_mode\":\""<<actuatorMode<<"\""
 <<",\"motor_command\":0,\"motor_applied_thrust\":0,\"motor_plugin_present\":false}";
 out.success=true;out.message=s.str();
 }catch(const std::exception&e){out.success=false;out.message=e.what();}return true;
 }
}; GZ_REGISTER_WORLD_PLUGIN(MigrationStep)
}
