"""Deterministic map families for R1, development and frozen evaluation seeds disjoint."""
import copy,math,random

def generate(base,count,seed,distances=(1000,)):
    rng=random.Random(seed);jobs=[]
    for i in range(count):
        length=distances[(i//12)%len(distances)]; family=('islands','channel','staggered','open')[i%4]
        profile=('stable','slow','fast')[(i//4)%3]
        angle=math.radians(rng.uniform(-65,65));c,s=math.cos(angle),math.sin(angle)
        def xy(x,y):return [c*x-s*y,s*x+c*y]
        circles=[]
        if family!='open':
            n=max(1,round(length/650))
            for k in range(n):
                x=length*(k+1)/(n+1)+rng.uniform(-45,45)
                ys=([-rng.uniform(240,340),rng.uniform(240,340)] if family=='channel' else
                    [rng.uniform(-65,65)] if family=='islands' else [(-1)**k*rng.uniform(110,190)])
                for y in ys:circles.append({'center_xy':xy(x,y),'entity_radius':rng.uniform(40,75),'safety_buffer':60.})
        suite=copy.deepcopy(base);scene={'id':f's{seed}_{i:03d}_{family}_{profile}_{length}',
            'seed':seed*100+i,'profile':profile,'base_direction_degrees':math.degrees(angle)+rng.choice([0,60,120,180,240,300])+rng.uniform(-12,12),
            'goal':xy(length,0),'map':'generated','distance_m':length,'layout':family,'split':'development' if seed==71 else 'frozen_test'}
        suite['maps']={'generated':circles};suite['world_bounds']=[-length-1600,length+1600,-length-1600,length+1600]
        suite['world_radius_limit_m']=length+2000;suite['task_time_limit_s']=int(1800*length/1000)
        suite['comparison_scenarios']=[scene];suite['capture_scenarios']=[];suite['limits']='R1 same episode time, bounds, field and evaluation safety for all methods'
        jobs.append((scene,suite))
    return jobs
