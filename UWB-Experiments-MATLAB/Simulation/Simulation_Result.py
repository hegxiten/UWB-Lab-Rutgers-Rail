"""
This py script will simulate the impact of relative velocity between transmitter
and receiver. The relative moion transmitter and receiver will result in doppler effect 
at tramsmitter and receiver resulting in change in perceived data rate at receiver  
"""

import math as m
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

units = {"Distance" : " (ft)", "Updates" : "", "Time":" (sec)", 
         "Speed":" (mph)"}

def geneatePlot(x,y,xlabel,ylable,title):
    fig1 = plt.figure()
    ax1 = fig1.add_subplot()
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylable)
    ax1.set_title(title)
    ax1.plot(x,y)
    
def geneatePlot2(x,ys,l,xlabel,ylable,title,ltitle):
    fig1 = plt.figure()
    ax1 = fig1.add_subplot()
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylable)
    ax1.set_title(title)
    for y in ys:
        ax1.plot(x,y)    
    leg1 = ax1.legend(l,bbox_to_anchor =(0.9, -0.15), ncol = len(l),title=ltitle)         
    


def impact_of_relativespeed():

    """
    This method plot the impact of relative velocity on the update rate.
    If the trasmitter moves towards receiver perceived update rate at receiver 
    increases by factor and if trasmitter moves away from  receiver perceived 
    update rate at receiver decreases by factor
    deltaT' = deltaT/sqrt(1 - (deltaV/c)^2)
    """
    # value of speed of light in mph
    c = 6.706e+8
    deltaSpeed = [ s for s in range(10, 50, 5)]
    
    # case transmitter is moving towards receiver 
    deltaTratio1 = np.round([1/m.sqrt(1 - (s/c)**2) for s in deltaSpeed],2)
    
    # case transmitter is moving away from receiver 
    deltaTratio2 = np.round([m.sqrt(1 - (s/c)**2) for s in deltaSpeed],2)
    # plot for Imapact of relative speed on data rate
    geneatePlot(deltaSpeed,deltaTratio1,"Relative Speed",
                "Change in data rate","Transmitter moving towords receiver")
    geneatePlot(deltaSpeed,deltaTratio2,"Relative Speed",
                "Change in data rate","Transmitter moving away receiver")    
    plt.show()
    



def impact_updatedate_relativespeed(dis,rspeed,dropProb,updaterate, threshold):
    """
    This method simulate the impact of updaterate and relative speed on 
    threshold reporting 
    """
    # in feets
    distance  = dis
    conversion  = 1.467
    # mph
    relativespeed = rspeed
    relativespeed = conversion * relativespeed
    # sec
    datarate = updaterate
    prob = dropProb
    updates = 0
    threshold  = threshold
    timeelapsed = 0
    while(True):
        # decrease distance with new update ()
        distance = distance - relativespeed*datarate
        # randomly decide if packet will be dropped
        dropped = np.random.choice(np.arange(2), 1, p=[1 - prob, prob])
        # if packet is not droppped then receiver will receive update and check
        # for threshold
        if not dropped:
            # receiver receives distance update
            updates +=1
            if distance<=threshold:
                return(distance,updates, np.round(timeelapsed*datarate,2))
        timeelapsed+=1
        

def impact_of_error(dis,rspeed,dropProb,updaterate, threshold,
                                    tech = "UWB"):
    """
    This method simulate the impact of updaterate and relative speed on 
    threshold reporting 
    """
    # in feets
    distance  = dis
    conversion  = 1.467
    # mph
    relativespeed = rspeed
    relativespeed = conversion * relativespeed
    # sec
    datarate = updaterate
    prob = dropProb
    updates = 0
    threshold  = threshold
    timeelapsed = 0
    while(True):
        # decrease distance with new update ()
        distance = distance - relativespeed*datarate
        if tech == "UWB":
            sigma = 0.32 # 10 cm
        elif tech == "BLE":
            sigma = 16.402
        error = np.random.normal(0, sigma, 1)[0]
        distance_reported = distance + error      
        # add error in this distance randomly ()
        # randomly decide if packet will be dropped
        dropped = np.random.choice(np.arange(2), 1, p=[1 - prob, prob])
        # if packet is not droppped then receiver will receive update and check
        # for threshold
        if not dropped:
            # receiver receives distance update         
            updates +=1
            if distance_reported <= threshold and distance > threshold:
                return 0
            elif distance_reported <= threshold and distance <= threshold:
                return 1
        timeelapsed+=1        


def impact_of_error_with_MD(dis,rspeed,dropProb,updaterate, threshold,
                                    tech = "UWB"):
    """
    This method simulate the impact of updaterate and relative speed on 
    threshold reporting 
    """
    # in feets
    distance  = dis
    conversion  = 1.467
    # mph
    relativespeed = rspeed
    relativespeed = conversion * relativespeed
    # sec
    datarate = updaterate
    prob = dropProb
    updates = 0
    threshold  = threshold
    timeelapsed = 0
    while(True):
        # decrease distance with new update ()
        distance = distance - relativespeed*datarate
        if tech == "UWB":
            sigma = 0.32 # 10 cm
        elif tech == "BLE":
            sigma = 3.2 #5 m
        error = np.random.normal(0, sigma, 1)[0]
        distance_reported = distance + error      
        # add error in this distance randomly ()
        # randomly decide if packet will be dropped
        dropped = np.random.choice(np.arange(2), 1, p=[1 - prob, prob])
        # if packet is not droppped then receiver will receive update and check
        # for threshold
        if not dropped:
            # receiver receives distance update         
            updates +=1
            if distance_reported > threshold and distance < threshold:
                return 0
            elif distance_reported <= threshold and distance > threshold:
                return 1
            elif distance_reported <= threshold and distance <= threshold:
                return 2
        timeelapsed+=1       
                

def run_probablity_simulation(simstep,dis,rspeed,updaterate, threshold):
    result = defaultdict(list)
    for p in np.round(np.arange(0,1,0.1),1):
        avgdis, avgdates,avgtime = (0,0,0)
        for i in range(simstep):
            tdis, tupdates, ttime = impact_updatedate_relativespeed(dis,rspeed,p,updaterate,threshold)
            avgdis+= tdis
            avgdates += tupdates
            avgtime += ttime
        result.update({p :np.round([avgdis/100, avgdates/100,avgtime/100],2)})
    
    for j,value in enumerate(["Distance", "Updates", "Time"]):
        x = list(result.keys())
        y = list(map(lambda key: (result.get(key))[j], result.keys()))
        geneatePlot(x,y,"Package Drop Probability",
                    value,"Package Drop Probability vs " + value)


def run_speed_simulation(simstep, dis,dropProb,updaterate, threshold):
    result = defaultdict(list)
    for s in range(2,25,2):
        avgdis, avgdates,avgtime = (0,0,0)
        avgtime = 0 
        for i in range(simstep):
            tdis, tupdates, ttime = impact_updatedate_relativespeed(dis,s,dropProb,updaterate,threshold)
            avgdis+= tdis
            avgdates += tupdates
            avgtime += ttime
        result.update({s :np.round([avgdis/simstep, avgdates/simstep,avgtime/simstep],2)})
    
    for j,value in enumerate(["Distance", "Updates", "Time"]):
        x = list(result.keys())
        y = list(map(lambda key: (result.get(key))[j], result.keys()))
        geneatePlot(x,y,"Relative Speed",
                    value,"Relative Speed vs " + value)
        

        
        
def run_datarate_simulation(simstep, dis,rspeed,dropProb,threshold):
    result = defaultdict(list)
    # datarate
    for d in [0.1, 0.2, 0.5, 1, 2]:
        avgdis, avgdates,avgtime = (0,0,0)
        avgtime = 0 
        for i in range(simstep):
            tdis, tupdates, ttime = impact_updatedate_relativespeed(dis,rspeed,dropProb,d,threshold)
            avgdis+= tdis
            avgdates += tupdates
            avgtime += ttime
        result.update({d:np.round([avgdis/simstep, avgdates/simstep,avgtime/simstep],2)})
    
    for j,value in enumerate(["Distance", "Updates", "Time"]):
        x = list(result.keys())
        y = list(map(lambda key: (result.get(key))[j], result.keys()))
        geneatePlot(x,y,"Update rate(sec)",
                    value,"Update rate vs " + value)         
        

def run_error_impact(simstep, dis,rspeed,dropProb,threshold):
    result = defaultdict(list)
    updaterate = 0
    for tech in ["BLE","UWB"]:
        if tech == "BLE":
            updaterate = 1
        else:
            updaterate = 0.1
        resulttemp = [impact_of_error(dis, rspeed, dropProb,updaterate, threshold,tech)
                  for i in range(simstep)]
        result.update({tech: [(resulttemp.count(0)/simstep)*100,(resulttemp.count(1)/simstep)*100]})
    
    
    for j,value in enumerate(["False Alarm % ", "True Detection %"]):
        fig1 = plt.figure()
        ax1 = fig1.add_subplot()
        ax1.set_xlabel("Technology")
        ax1.set_ylabel(value)
        ax1.set_title("Ranging Tech vs %s for threshold %d ft" % (value,threshold))
        x = list(result.keys())
        y = list(map(lambda key: (result.get(key))[j], result.keys()))
        ax1.bar(x, y)        
        

def run_error_impact_withMD(simstep, dis,rspeed,dropProb,threshold):
    result = defaultdict(list)
    # datarate
    for tech in ["BLE","UWB"]:
        if tech == "BLE":
            updaterate = 1
        else:
            updaterate = 0.1
        resulttemp = [impact_of_error_with_MD(dis, rspeed, updaterate, dropProb,threshold,tech)
                  for i in range(simstep)]
        result.update({tech: [(resulttemp.count(0)/simstep)*100,(resulttemp.count(1)/simstep)*100,
                              (resulttemp.count(2)/simstep)*100]})
    
    
    for j,value in enumerate(["Missed Detection % ", "False Alarm % ", "True Detection %"]):
        fig1 = plt.figure()
        ax1 = fig1.add_subplot()
        ax1.set_xlabel("Technology")
        ax1.set_ylabel(value)
        ax1.set_title("Ranging Tech vs %s for threshold %d ft" % (value,threshold))
        x = list(result.keys())
        y = list(map(lambda key: (result.get(key))[j], result.keys()))
        ax1.bar(x, y)        
        
               
def scenario(simstep,dis,dropProb,threshold,r_speed):
    result = {}
    update_rate =  [0.1, 0.2, 0.5, 1, 2]
    for rs in r_speed:
        t_res = {}
        for ur in update_rate:
            avgdis, avgdates,avgtime = 0,0,0
            for i in range(simstep):
                tdis, tupdates, ttime = impact_updatedate_relativespeed(dis,rs,dropProb,ur,threshold)
                avgdis+= tdis
                avgdates += tupdates
                avgtime += ttime
            t_res.update({ur:np.round([avgdis/simstep, avgdates/simstep,avgtime/simstep],2)})
        result[rs] = t_res
    for j,value in enumerate(["Distance", "Updates", "Time"]):
        x = update_rate
        ys = []
        for rs in r_speed:
            y = list(map(lambda key: (result.get(rs))[key][j], update_rate))
            ys.append(y)
        geneatePlot2(x,ys,r_speed,"Updaterate(sec)",
            value + units[value],"Updaterate(sec) vs " + value + 
            " \n(for different relative speed)","Relative Speeds " + units["Speed"] )
    
            
        
# Scenario1
# scenario(1000,150,0.1,50,list(range(2,12,2)))
# Scenario2
# scenario(1000,1500,0.1,300,list(range(10,60,10)))


# # Distance = 1500ft, prob = 0.1, relative speed = 5mph,Threshold = 300ft
run_error_impact(1000,1500, 25,0.1,300)

# # Distance = 150ft, prob = 0.1, relative speed = 5mph,Threshold = 50ft
# run_error_impact(1000,150, 5, 0.1,50)
run_error_impact(1000,150, 5,0.1,50)

plt.show()