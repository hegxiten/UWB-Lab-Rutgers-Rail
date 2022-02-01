import os
from time import sleep
import fnmatch
import os
isExist = os.path.exists("myfile.txt") 
if isExist:
    print("new File created")
    newFile = open("myfile.txt", "w")
for f in os.listdir('.'): 
    if os.path.isfile(f) and fnmatch.fnmatch(f, 'POS*.txt'):
        File = open(f,'r')
        count=1
        for lines in File:
            newFile = open("myfile.txt", "a")
            newFile.write(lines);
            newFile.close();
            print(count);
            count+=1;
        File.close();

    
