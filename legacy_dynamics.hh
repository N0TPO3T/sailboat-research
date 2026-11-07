#pragma once
#include "legacy_parameters.hh"
#include <stdexcept>
namespace legacy {
inline double wrap(double x){return std::atan2(std::sin(x),std::cos(x));}
inline State derivative(const State& s,double sail,double rudder,double wx,double wy) {
 const double phi=s[2],psi=s[3],u=s[4],v=s[5],p=s[6],r=s[7];
 const double cp=std::cos(phi),sp=std::sin(phi),cy=std::cos(psi),sy=std::sin(psi);
 const double safe=(cp>=0?1.:-1.)*std::max(std::abs(cp),1e-3);
 const double windScale=std::log(std::max(std::abs(P_z_s)*std::max(cp,0.)/P_h0,1.))/std::log(P_h1/P_h0);
 const double awu=windScale*(cy*wx+sy*wy)-u;
 // Upstream broadcasts the (3,) cross product across a (3,1) array.
 // Its [1][0] subtracts cross.x (zero), not cross.y. Preserve actual loaded semantics.
 const double awv=cp*windScale*(-sy*wx+cy*wy)-v;
 const double aa=std::atan2(awv,-awu),as=wrap(aa-sail)*180/M_PI;
 const double Ls=.5*P_rho_a*(awu*awu+awv*awv)*P_As*sail_cl(as),Ds=.5*P_rho_a*(awu*awu+awv*awv)*P_As*sail_cd(as);
 const double sx=Ls*std::sin(aa)-Ds*std::cos(aa),syf=Ls*std::cos(aa)+Ds*std::sin(aa);
 double tau[4]={sx,syf,-syf*P_zs,-sx*P_Xce*std::sin(sail)+syf*(P_Xm-P_Xce*std::cos(sail))};
 const double aru=-u+r*P_yr,arv=-v-r*P_xr+p*P_zr,ar=std::atan2(arv,-aru),arDeg=wrap(ar-rudder)*180/M_PI;
 const double clr=rudder_cl(arDeg),cdr=rudder_cd(arDeg)+clr*clr*P_Ar/(M_PI*2*P_zeta_r*P_d_r*P_d_r);
 const double lr=.5*P_rho_w*P_Ar*(aru*aru+arv*arv)*clr,dr=.5*P_rho_w*P_Ar*(aru*aru+arv*arv)*cdr;
 const double rx=lr*std::sin(ar)-dr*std::cos(ar),ry=lr*std::cos(ar)+dr*std::sin(ar);
 tau[0]+=rx;tau[1]+=ry;tau[2]-=ry*P_zr;tau[3]+=ry*P_xr;
 const double aku=-u+r*P_yk,akv=-v-r*P_xk+p*P_zk,ak=std::atan2(akv,-aku),akDeg=wrap(ak)*180/M_PI;
 const double clk=keel_cl(akDeg),cdk=keel_cd(akDeg)+clk*clk*P_Ak/(M_PI*2*P_zeta_k*P_d_k*P_d_k);
 const double lk=.5*P_rho_w*P_Ak*(aku*aku+akv*akv)*clk,dk=.5*P_rho_w*P_Ak*(aku*aku+akv*akv)*cdk;
 double D[4]={-lk*std::sin(ak)+dk*std::cos(ak),-lk*std::cos(ak)-dk*std::sin(ak),0,0};
 D[2]=-D[1]*P_zk;D[3]=-(lk*std::cos(ak)+dk*std::sin(ak))*P_xk;
 const double ahu=-u+r*P_yh,ahv=(-v-r*P_xh+p*P_zh)/safe,ah=std::atan2(ahv,-ahu),fr=hull_resistance(std::hypot(aku,akv));
 D[0]+=fr*std::cos(ah);D[1]+=-fr*std::sin(ah)*cp;D[2]+=fr*std::sin(ah)*cp*P_zh;D[3]+=-fr*std::sin(ah)*cp*P_xh;
 D[2]+=P_c*p*std::abs(p);D[3]+=P_d*(cp*r)*std::abs(cp*r)*cp;
 const double phid=phi*180/M_PI;double G[4]={0,0,P_a*phid*phid+P_b*phid,0};
 const double added=P_a22*v+P_a24*p+P_a26*r;
 double Cnu[4]={-P_m*r*v-added*r,P_m*r*u+P_a11*u*r,0,added*u-P_a11*u*v};
 double rhs[4];for(int i=0;i<4;i++)rhs[i]=-Cnu[i]-D[i]-G[i]+tau[i];
 State out={cy*u-sy*cp*v,sy*u+cy*cp*v,p,cp*r,0,0,0,0};
 for(int i=0;i<4;i++)for(int j=0;j<4;j++)out[i+4]+=MI[i][j]*rhs[j];
 // Preserve upstream nan_to_num; fail on nonfinite integration states separately.
 for(auto &z:out){if(std::isnan(z))z=0;else if(std::isinf(z))z=z>0?1e3:-1e3;}
 return out;
}
inline State rk4(const State& s,double t,double dt,double sail0,double rudder0,double ds,double dr,double wx,double wy){
 auto f=[&](const State& y,double q){return derivative(y,sail0+q*ds,rudder0+q*dr,wx,wy);};
 auto add=[&](const State& a,double scale){State v;for(int i=0;i<8;i++)v[i]=s[i]+scale*a[i];return v;};
 auto a=f(s,t),b=f(add(a,dt/2),t+dt/2),c=f(add(b,dt/2),t+dt/2),d=f(add(c,dt),t+dt);State y;
 for(int i=0;i<8;i++){y[i]=s[i]+dt*(a[i]+2*b[i]+2*c[i]+d[i])/6;if(!std::isfinite(y[i]))throw std::runtime_error("legacy4dof integration nonfinite");}return y;
}
}
