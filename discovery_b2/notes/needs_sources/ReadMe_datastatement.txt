
****************************************************************************************
|                                     Data statement                                   |
|                            //First published 03.10.2024//                            |
|                                     For the study:                                   |
|                                Carlsen et al., in rev.                               |
| "Autonomous data sampling for high-resolution spatiotemporal fish biomass estimates" |
****************************************************************************************

The publiction depended on versions of a dataset, all three available here.

(1) xdat.Full:
The full dataset, with highest available resolution. 
For Models 1,2,3,4,7,9.


(2) xdat.21_23:
A subset of the full dataset for Years 2021-2023, where USV sampled environmental variables are included . 
For Models 5 and 6 (ref. Carlsen et al., in rev.).


(3) xdat.Agg:
Aggregated data (2x2 km2).
For Model 8 and "aggregated" spatial prediction.



************************************
*       Variable explanations:     *
*   See publication for details in *
* Table 1, Carlsen et al., in rev.:*
************************************
All variables are explined in Table 1 (below, but see Carlsen et al., for higher readability).

//Necessary explanation of variable abbrevations://
CMSI variables:
SO_surf = CMSI provided Salinity 
Mean_thetao_SST = CMSI provided Temperature
Chl_surf = CMSI provided surface Chlorophyll
Mean_NS_vo_Wclm = CMSI provided North-South currents
Mean_EW_uo_Wclm = CMSI provided East-West currents
Mean_current_speed = CMSI provided Current speed
Depth = CMSI provided topographic depth (i.e. depth of seabed)

X,Y = coordinates 

USV variables (only in xdat.21_23):
SB_CTCond = USV measured surface Salinity
SB_CTTemp = USV measured surface Temperature
SB_ECO3_CHL = USV measured surface Chlorophyll


************************************* Table 1: ********************************************

Variable	Unit	Sensitivity	Resolution	Total sensor range	Variable range	Source	Collection method	Variable status
Nautical Area Scattering Coefficient (NASC)	m2 nmi−2		Hourly mean		0.0001 - 8000	 USV 	Simrad WBT mini, 70cm depth	Observation
Salinity
	Mmhos
 /cm	+/- 0.005	Hourly mean	0-60	0- 11.9	USV	NBOSI CT 40cm depth  	 Observation,  Sea surface  
Temperature (Temp)	°C	+/- 0.002	Hourly mean	0-30	3.1-25.9	USV	NBOSI CT 40cm depth	 Observation,  Sea surface  
Chlorophyll
(Chl)	μg/l 	+-0.025	 Hourly mean 	0-50	0-7.3	USV	Sea Bird ECO triplet 20cm depth	 Observation,  Sea surface
Salinity
	PSU (~Mmhos/cm)	-0.01
	Monthly and daily on 2x2km grid		6.3-7.4	CMSI
(Anonymous c,  Anonymous d)	Moored monitoring stations, CTD and ferry boxes	Estimate,
Sea surface
Temperature
(Temp)	°C	0-5m: -0.4
5-30m: 0.1 
30-80:m 0.3
80-200: 0.3	Monthly and daily on 2x2km grid		3.3-20.6	CMSI
(Anonymous c,  Anonymous d)	Moored monitoring stations , CTD, L3 satellite imagery and ferry boxes	 Estimate, Sea surface
Chlorophyll
(Chl)		-0.72	Monthly and daily on 2x2km grid		0.5-4.1	CMSI 
(Anonymous a,  Anonymous b)	 Moored monitoring stations , CTD, L3 satellite imagery and ferry boxes 	 Estimate,  Sea surface
North-South currents
(NS_current)	m/s	-0.08 - 0.23 m/s 
-17° - 38°	Monthly on 2x2km grid		-0.1-0.1	CMSI
(Anonymous c,  Anonymous d)	Moored monitoring stations	 Estimate, weighted average of water column
 East-West 
currents
(EW_current)	m/s	-0.08 - 0.23 m/s
-17° - 38°	Monthly on 2x2km grid		-0.1-0.1	CMSI
(Anonymous c,  Anonymous d)	Moored  monitoring stations	 Estimate, weighted average of water column
Current speed	m/s	-0.08 - 0.23 m/s 	Monthly on 2x2km grid		0.003-0.128	CMSI
(Anonymous c,  Anonymous d)	Moored  monitoring stations	 Estimate
Depth of seabed (Depth)	meter	-749 - 0	2x2km grid		-166.4 - 0	CMSI (Anonymous a)		Observation
Week	Julian week				16-31	USV		 Observation  
Hour 	Cyclic 24 hour				00-23	USV		 Observation 
Year	Julian year				2019-2023	USV		 Observation 
Month	Julian month				4-7	USV		Observation
X,Y	UTM coordinates,  CRS 33N				X: 619.4-697.1
Y: 6290-6311
	Calculated from USV latitude, longitude		Observation
