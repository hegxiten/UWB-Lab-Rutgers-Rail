def main():
    #Declare the path of the filename you want to use
    filename = "D:\\UWB_FRA_Project\\UWB-Lab-Rutgers-Rail\\UWB-Experiments-MATLAB\\uwb_ranging_fieldtest_results\\Static\\2021-05-25-11-00-35-data-B-raw_log.log"

    #Library is imported
    import pandas as pd

    #Initial values are declared
    df = pd.DataFrame(columns=['Date', 'Time (HH:MM:SS)', 'Master', 'Slave','Distance'])
    i = 0
    masters = {'45BA': '88BA', '0B8A': '88BA', '1912': '0C1A', '47A3': '0C1A'}

    #File is processed depending on whether it is a raw file or a processed file.
    if "processed_log" in filename:
        with open(filename, "r") as file:
            while True:
                #Data is read line by line
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
                        Distance = int(part1[-1].split('}')[0])
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

    elif "raw_log" in filename:
        print("Please select a processed log file")    
        
    else:
        print("Invalid filename. Please make sure to input a valid log file.")

    #Dataframe is cleaned by removing null and negative values
    df = df[df.Master.notnull()]
    df.drop(df[df['Distance'] <= 0].index , inplace=True)

    #Dataframe is converted into csv file
    if "processed_log" in filename:
        converted_filename = "PostProcessed_" + filename[len(filename)-49:len(filename)-4] + ".csv"
        df.to_csv(converted_filename, index=False)
    elif "raw_log" in filename:
        converted_filename = "PostProcessed_" + filename[len(filename)-38:len(filename)-4] + ".csv"
        df.to_csv(converted_filename, index=False)

    #Final processed dataframe is printed. Additonal data analysis can be done using it.
    print (df)
        
if __name__ == "__main__":
    main()
