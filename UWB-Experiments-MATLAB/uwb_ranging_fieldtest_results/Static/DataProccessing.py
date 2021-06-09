#Library is imported
import pandas as pd

#Initial values are declared
df = pd.DataFrame(columns=['Date', 'Time (HH:MM:SS)', 'Master', 'Slave','Distance (in cm)'])
i = 0
masters = {'45BA': '88BA', '1912': '0C1A'}

#File is processed. Please define the path of the file you want to use below.
with open("D:\\UWB_FRA_Project\\UWB-Lab-Rutgers-Rail\\UWB-Experiments-MATLAB\\uwb_ranging_fieldtest_results\\Static\\2021-05-25-09-35-42-data-B-user-processed_log.log", "r") as file:
    while True:
        data = file.readline()
        if not data:
            break
        #Ignores the first line
        if "UTC TIME REFERENCE" in data:
            continue
        #Parses the data into variables and cleans it
        elif "uwb data:" in data:
            part = data.split()
            Date = part[0].split('[')[1]
            Time = part[1]
            data1 = file.readline()
            part1 = data1.split()
            if len(part1)>10:
                Slave = part1[10].split("'")[1]
                Distance = part1[-1].split('}')[0]
                Master = masters.get(Slave)
            else:
                Slave = "0"
        else:
            continue
        
        #Appends the data into the dataframe
        if Slave == "0":
            continue
        else:
            df.loc[i] = [Date] + [Time] + [Master] + [Slave] + [Distance]
            i = i + 1

#Prints the complete dataframe. Additional data analysis can be done using this dataframe.
print (df)
    

