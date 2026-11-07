#include "legacy_dynamics.hh"
#include <iostream>
#include <iomanip>
int main(){legacy::State s;double sail,rudder,wx,wy;std::cout<<std::setprecision(17);while(std::cin>>s[0]){for(int i=1;i<8;i++)std::cin>>s[i];std::cin>>sail>>rudder>>wx>>wy;auto d=legacy::derivative(s,sail,rudder,wx,wy);for(double v:d)std::cout<<v<<" ";std::cout<<"\n";}}
