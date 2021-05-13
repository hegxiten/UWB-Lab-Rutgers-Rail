import numpy as np
import matplotlib.pyplot as plt
import math

# Class to simulate a vehicle it has mobility properties - inital speed, 
# starting dstance, maximum accelaration and ranging properties like updaterate 
# and ranging error (depending tecg being used)
class vehicle:
    # for stationary vehicles starting_speed = 0
    def __init__(self,id,starting_speed,starting_distance, updaterate,alpha,beta,sigma):
        self.id =  id
        self.speed = starting_speed
        self.distance =  starting_distance
        self.alpha = alpha
        self.beta = beta
        self.updaterate = updaterate
        self.range = None
        self.prev_range = None
        self.sigma = sigma
        self.time_to_collide = []
    
            
     # function to update speed based on accelaration 
    def update_speed(self,time):
        if isinstance(time*self.updaterate, int) or (time*self.updaterate).is_integer():
            self.speed = (self.alpha/self.beta) * (1 - math.exp(-self.beta*1)) + self.speed * math.exp(-self.beta*1)
    
    # function to update distance based on speed and distance of movement.
    def update_distance(self,direction):
        if direction == "to":
            self.distance = round(self.distance - self.speed*self.updaterate,2)
        elif direction == "aw":
            self.distance = round(self.distance + self.speed*self.updaterate,2)
    
    # function to update distance based on speed and distance of movement.
    def update_properties(self,time,direction):
        if self.speed == 0:
            return 
        self.update_speed(time)
        self.update_distance(direction)
    
    # function to get range readings. Here normal distribution is 
    # used to generate the error.
    def update_reported_range(self,rrange,prob):
        if not np.random.choice(np.arange(2), 1, p=[1 - prob, prob]):
            self.prev_range = self.range
            error = np.random.normal(0, self.sigma, 1)[0]
            self.range = round(rrange + error,2) 
            if self.range and self.prev_range:
                self.time_to_collide.append(self.range/(abs(self.prev_range-self.range)/self.updaterate))
            else:
                if self.time_to_collide and  self.time_to_collide[-1]:
                    self.time_to_collide.append(self.time_to_collide[-1])

    
              
# function to generate 
def scenarios_with_just_thres(v1speed,v1dist,dir1,v2speed,v2dist,dir2,thres,prob,updaterate,
                              alpha,beta,sigma):
    conversion  = 1.467
    updaterate = updaterate
    prob = prob    
    v1 = vehicle(1,v1speed*conversion,v1dist,updaterate,alpha,beta,sigma)        
    v2 = vehicle(2,v2speed*conversion,v2dist,updaterate,alpha,beta,sigma)
    t = 0
    thres = thres
    a1 = []
    a2 = []
    # time_to_collide = []
    prev = v2dist
    while(True):
        v1.update_properties(t, dir1)
        v2.update_properties(t, dir2)
        distance_bw_vehicles = abs(v1.distance - v2.distance)
        time_to_collide = distance_bw_vehicles/(abs(prev - distance_bw_vehicles)/updaterate)
        prev = distance_bw_vehicles
        v1.update_reported_range(distance_bw_vehicles,prob)
        v2.update_reported_range(distance_bw_vehicles,prob)
        t +=1
        if distance_bw_vehicles<=thres:
            if v1.range and v1.range<=thres:
                a1.append(1)
            else:
                a1.append(-1)
            if v2.range and v2.range<=thres:
                a2.append(1)
            else:
                a2.append(-1)
            if a1[-1] == 1 or a2[-1] == 1:
                return round(time_to_collide,2),v1.time_to_collide[-1],v2.time_to_collide[-1]
   
def scenario1(simStep,updaterate,load,tech):
    if tech=="UWB":
        sigma = 0.32
    elif tech =="BLE":
        sigma = 3.2
    if load =="Light":
        alpha = 6.3 
        beta = 0.02
    elif load =="Heavy":
        alpha = 3.3
        beta = 0.04
    v2_speed_list = [3, 5, 10 ,15, 20, 25]
    data = dict()
    for speed in v2_speed_list:
        time_to_collide_actual = 0
        time_to_collide_v2 = 0
        if speed > 5:
            thres = 300
            dist = 1500
        else:
            thres = 50
            dist = 150
        for _ in range(simStep):
            t,_,t2= scenarios_with_just_thres(0,0,"aw",speed,dist,"to",thres,0.1,updaterate,
                                              alpha,beta,sigma)
            time_to_collide_actual +=t
            time_to_collide_v2 +=t2
        data.update({speed:[round(time_to_collide_actual/simStep,2),
                            round(time_to_collide_v2/simStep,2)]})
        
    fig1 = plt.figure()
    ax1 = fig1.add_subplot()
    ax1.set_xlabel("Initial Relative Speed(mph)")
    ax1.set_ylabel("Available reaction time(sec)")
    ax1.set_title("Realtive Speed vs Available reaction time(sec) for " + tech + " ("+ load + " load vehicle)")
    x = list(data.keys())                      
    for j,value in enumerate(["Actual", "Vehicle2"]):
        y = list(map(lambda key: (data.get(key))[j], data.keys()))
        ax1.plot(x,y,label = value,linestyle='--',marker = "o")
    ax1.axvline(10,label='Threshold changes from 50ft to 300ft\n Starting distance from 150ft to 1500ft'
                ,c = 'r',linestyle='--')
    leg1 = ax1.legend(bbox_to_anchor =(1,1))               
    

def scenario2(simStep,updaterate,load,tech):
    if tech=="UWB":
        sigma = 0.32
    elif tech =="BLE":
        sigma = 3.2
    if load =="Light":
        alpha = 6.3 
        beta = 0.02
    elif load =="Heavy":
        alpha = 3.3
        beta = 0.04    
    speed_list = [(2,5),(5, 7) , (5, 10) , (8, 12), (10, 15),
                  (15, 15),(20, 15), (20, 25), (25, 25)]
    data = dict()
    for v1, v2 in speed_list:
        time_to_collide_actual = 0
        time_to_collide_v1 = 0
        time_to_collide_v2 = 0
        if v1 > 5 or v2 > 5 :
            thres = 300
            dist = 1500
        else:
            thres = 50
            dist = 150
        for _ in range(simStep):
            t,t1,t2= scenarios_with_just_thres(v1,0,"aw",v2,dist,"to",thres,0.1,updaterate,
                                              alpha,beta,sigma)
            time_to_collide_actual +=t
            time_to_collide_v1 +=t1
            time_to_collide_v2 +=t2
        data.update({v2+v1:[round(time_to_collide_actual/simStep,2),
                            round(time_to_collide_v1/simStep,2),
                            round(time_to_collide_v2/simStep,2)]})
        
    fig1 = plt.figure()
    ax1 = fig1.add_subplot()
    ax1.set_xlabel("Initial Relative Speed(mph)")
    ax1.set_ylabel("Available reaction time(sec)")
    ax1.set_title("Realtive Speed vs Available reaction time(sec) for " + tech + " ("+ load + " load vehicle)")
    x = list(data.keys())                      
    for j,value in enumerate(["Actual","Vehicle1","Vehicle2"]):
        y = list(map(lambda key: (data.get(key))[j], data.keys()))
        ax1.plot(x,y,label = value,linestyle='--',marker = "o") 
    ax1.axvline(15,label='Threshold changes from 50ft to 300ft\n Starting distance from 150ft to 1500ft'
                ,c = 'r',linestyle='--')
    leg1 = ax1.legend(bbox_to_anchor =(1,1))     

def scenario3(simStep,updaterate,load,tech):
    if tech=="UWB":
        sigma = 0.32
    elif tech =="BLE":
        sigma = 3.2
    if load =="Light":
        alpha = 6.3 
        beta = 0.02
    elif load =="Heavy":
        alpha = 3.3
        beta = 0.04      
    speed_list = [(5, 2),(5, 1),(25, 5),(25, 2),(25, 1)]
    data = dict()
    for v1, v2 in speed_list:
        print(v1,v2)
        time_to_collide_actual = 0
        time_to_collide_v1 = 0
        time_to_collide_v2 = 0
        if v1 > 5 or v2 > 5 :
            thres = 300
            dist = 1500
        else:
            thres = 50
            dist = 150
        for _ in range(simStep):
            t,t1,t2= scenarios_with_just_thres(v1,0,"aw",v2,dist,"aw",thres,0.1,updaterate,
                                              alpha,beta,sigma)
            time_to_collide_actual +=t
            time_to_collide_v1 +=t1
            time_to_collide_v2 +=t2
        data.update({abs(v1-v2):[round(time_to_collide_actual/simStep,2),
                            round(time_to_collide_v1/simStep,2),
                            round(time_to_collide_v2/simStep,2)]})
        
    fig1 = plt.figure()
    ax1 = fig1.add_subplot()
    ax1.set_xlabel("Speed(mph)")
    ax1.set_ylabel("Available reaction time(sec)")
    ax1.set_title("Relative Speed vs Available reaction time(sec)")
    x = list(data.keys())                      
    for j,value in enumerate(["Actual","Vehicle1","Vehicle2"]):
        y = list(map(lambda key: (data.get(key))[j], data.keys()))
        ax1.plot(x,y,label = value,linestyle='--',marker = "o") 
    leg1 = ax1.legend(loc='upper right')                
        
 
    

# scenario 1 
# scenario1(200,0.1,"Light","UWB")
# scenario1(200,0.1,"Heavy","UWB")
# # # scenario2
# scenario2(200,0.1,"Light","UWB")
# scenario2(200,0.1,"Heavy","UWB")
# scenario3(100)
scenario3(100,0.1,"Light","UWB")
#scenario3(200,0.1,"Heavy","UWB")
#print(scenarios_with_just_thres(5,0,"aw",1,150,"aw",50,0.1,0.1,6.3,0.02,0.32))




