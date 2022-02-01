function collectAndPlot()
    global scriptStatus expName;
    scriptStatus = "ST";  
    cleanup = onCleanup(@()myCleanup());
    try
        %Getting name of the experiment
        expName = input("Enter the name of the experiment: ",'s');
    
        %Checking if previous data of experiment is present
        useExistingValues = "N";
        if exist(expName+"/LastExpVar.mat", 'file')
            existingValuePrompt = "Do you want to use existing experimental variables?(Y/N) ";
            useExistingValues = input(existingValuePrompt,'s');
            while(~strcmpi(useExistingValues,"Y") && ~strcmpi(useExistingValues,"N"))
                useExistingValues = input("Input invalid. " + existingValuePrompt,'s');
            end
        end
        
        if(strcmpi(useExistingValues,"Y"))
            load(expName+"/LastExpVar","x_anch_pos","y_anch_pos","x_true","y_true");
            
        elseif(strcmpi(useExistingValues,"N"))
            %Getting experiment configuration
            [positions, duration, waitTime, readerCheckTime] = expConfigSetup();
            
            %Getting anchor information
            %Z axis values of are zero-padded by default. 
            %To input Z axis, use expAnchorGet('zPadding','N')
            [x_anch_pos, y_anch_pos] = expAnchorGet();
            
            %Ground truth
            x_true = zeros(1,positions);
            y_true = zeros(1,positions);
            
            % Writing files for the Positions
            initialpos = 1;
            flag=0;
            modeGetPrompt = "What is the mode of data collection? (Serial/MQTT): ";
            modeOfDataCollection = input(modeGetPrompt,'s');
            while(~strcmpi(modeOfDataCollection,"Serial") && ~strcmpi(modeOfDataCollection,"MQTT"))
                modeOfDataCollection = input("Input invalid. " + modeGetPrompt,'s');
            end
            mkdir (expName);
            if(strcmpi(modeOfDataCollection,"Serial"))
                serialPortName = input("Enter the serial port name (string): ",'s');
                port = serialport(serialPortName,115200,"Timeout",30);
                cd (expName);
                WritePosFileUsingSerialPort(initialpos,positions,...
                    duration,waitTime,readerCheckTime,port,flag);
            elseif(strcmpi(modeOfDataCollection,"MQTT"))
                [mqttObj, mysub] = tagMqttSubscriptionInit(0);
                cd (expName);
                WritePosFileUsingMQTT(initialpos,positions,...
                    duration,waitTime,readerCheckTime,mqttObj,mysub,flag);
            end
        end
        
        %Skip ploting if we don't want it writen now 
        plotNowPrompt = "Do you want to plot data rightnow?(Y/N) ";
        plotNow = input(plotNowPrompt,'s');
        while(~strcmpi(plotNow,"Y") && ~strcmpi(plotNow,"N"))
            plotNow = input("Input invalid. " + plotNow,'s');
        end
        
        if(strcmpi(plotNow,"Y"))
            cd ..
            GeoExp(x_anch_pos,y_anch_pos,x_true,y_true,expName);
            cd(expName)
        end
        
        cd ..
        movefile(expName,'../LabOutdoor/');
        fprintf("Moved files to LabOutdoor directory for future plotting \n")
        
   catch ME
       fprintf("\n"+ME.identifier);
       beep;
       rethrow(ME);
   end
   scriptStatus = "FT";

end

function WritePosFileUsingSerialPort(initialpos,positions,duration,waitTime,readerCheckTime,sP,flag)
    try  
        fprintf("[Serialport] Collecting from Position %d, total Positions: %d", initialpos, positions);
        initialpos = double(initialpos); positions = double(positions);
        for i = linspace(initialpos,positions,(positions-initialpos)+1)          
            fprintf("[Serialport] Checking the status of serial port\n");
            initSerialIncomingBytes = sP.NumBytesAvailable;
            flush(sP);
            delayTimer(readerCheckTime);
            
            if(initSerialIncomingBytes == sP.NumBytesAvailable)
                portHealthy = 0;
            else
                portHealthy = 1;
            end
                
            if(portHealthy)
                fprintf("[Serialport] Status of serial port is healthy, data recording after wait time is over\n\n");
                fileName="pos"+string(i)+".txt";
                fprintf("[Serialport] " + fileName + " collecting in progress");
                fileID = fopen(fileName,'w');
                delayTimer(duration*60);
                tStart=tic;%starts the timer
                flush(sP);
                while(true)
                    data = readline(sP);
                    fprintf(fileID,data+"\n");
                    if(toc(tStart)>duration*60)
                        disp("[Serialport] Done with the file");
                        while(i~=positions)
                            confirmation = input("[Serialport] Please confirm location tag has changed? (Y/N) ", 's');    
                            if(strcmpi(confirmation, "Y"))
                                break;
                            end
                        end
                        break;
                    end
                end
                
            elseif(~portHealthy)
                ME = MException('Serialport:NoBytesAvailable', ...
                '[Serialport] Listener Not in Reporting Mode');
                beep;
                throw(ME);
            end
        end
        
    catch ME
        if(strcmp(ME.identifier,'Serialport:NoBytesAvailable'))
            uiwait(msgbox('Please check the location of listener with respect to tag',...
                'Reader Data Error!!!!','error'));
            flag=flag+1;
            fprintf("[Serialport] flag: %d", flag);
            WritePosFileUsingSerialPort(i,positions,duration,waitTime,readerCheckTime,sP,flag);
        else
            rethrow(ME);
        end
    end
    fclose("all");
end




function WritePosFileUsingMQTT(initialpos,positions,duration,waitTime,readerCheckTime,mqttObj,msub,flag)
    try  
        fprintf("[MQTT/Wi-Fi Backbone] Collecting from Position %d, total Positions: %d\n", initialpos, positions);
        initialpos = double(initialpos); positions = double(positions);
        pause(1);
        for i = linspace(initialpos,positions,(positions-initialpos)+1)          
            fprintf("[MQTT/Wi-Fi Backbone] Checking the status of subscriber\n");
            sampleData = jsondecode(read(msub));
            initFrameNumeber = sampleData.superFrameNumber;
            delayTimer(readerCheckTime);
            
            if(initFrameNumeber == jsondecode(read(msub)).superFrameNumber)
                mqttHealthy = 0;
            else
                mqttHealthy = 1;
            end
            
            if(mqttHealthy)
                fprintf("[MQTT/Wi-Fi Backbone] Status of mqtt subcriber is healthy, data recording after wait time is over\n\n");
                fileName="pos"+string(i)+".txt";
                fprintf("[MQTT/Wi-Fi Backbone] " + fileName + " collecting in progress");
                fileID = fopen(fileName,'w');
                delayTimer(duration*60);
                tStart=tic;%starts the timer
                lastSuperFrameNbr = 0;
                while(true)
                    pause(0.001)
                    positionData = jsondecode(read(msub));
                    if(lastSuperFrameNbr ~= positionData.superFrameNumber)
                        lastSuperFrameNbr = positionData.superFrameNumber;
                        tag = extractBetween(positionData.tag_id,strlength(positionData.tag_id)-3,strlength(positionData.tag_id));
                        data = "POS,0," + tag +","+positionData.est_pos.x+","+positionData.est_pos.y+","+positionData.est_pos.z+","+positionData.est_qual+","+"x0A"+","+positionData.superFrameNumber;
                        fprintf(fileID,data+"\n");
                        if(toc(tStart)>duration*60)
                            disp("[MQTT/Wi-Fi Backbone] Done with the file");
                            while(i~=positions)
                                confirmation = input("[MQTT/Wi-Fi Backbone] Please confirm location tag has changed? (Y/N) ", 's');    
                                if(strcmpi(confirmation, "Y"))
                                    break;
                                end   
                            end
                            break;
                        end
                    end
                end
                
            elseif(~mqttHealthy)
                ME = MException('myComponent:inputErrorMQTT', ...
                    '[MQTT/Wi-Fi Backbone] Data received is not updated reconnecting');
                    beep;
                    throw(ME);    
            end
        end
    catch ME
        if(strcmp(ME.identifier,'myComponent:inputErrorMQTT'))
            uiwait(msgbox('Please check the subcriber status manually',...
                'Reader Data Error!!!!','error'));
            flag=flag+1;
            fprintf("[MQTT/Wi-Fi Backbone] flag: %d", flag);
            WritePosFileUsingMQTT(i,positions,duration,waitTime,readerCheckTime,mqttObj,msub,flag);
        else
            rethrow(ME);
        end   
    end
    fclose("all");
end


function [positions, duration, waitTime, readerCheckTime] = expConfigSetup()
    %Getting number of the positions
    promptPositionGet = "Enter the number of positions: ";
    positions = uint32(sscanf(input(promptPositionGet, 's'), '%d'));
    while(isempty(positions) || ~isa(positions,'integer') || (positions < 1))
        positions = uint32(sscanf(input("Input Invalid. " + promptPositionGet, 's'), '%d'));
    end

    %Getting time duration of positioning data collection, in minutes
    promptDurationGet = "Enter the time duration in minutes for each position (in mins): ";
    duration = double(sscanf(input(promptDurationGet,'s'),'%f'));
    while(isempty(duration) || ~isa(duration,'numeric') || (duration < 0))
        duration = double(sscanf(input("Input Invalid. " + promptDurationGet,'s'),'%f'));
    end

    %Getting time in seconds after which recording starts
    promptWaitTimeGet = "Enter the time duration to wait before recording starts (in secs): ";
    waitTime = double(sscanf(input(promptWaitTimeGet,'s'),'%f'));
    while(isempty(waitTime) || ~isa(waitTime,'numeric') || (waitTime < 0))
        waitTime = double(sscanf(input("Input Invalid. " + promptWaitTimeGet,'s'),'%f'));
    end

    %Getting time to verify reader operation 
    promptReaderCheckTimeGet = "Enter the reader check testing time (in secs): ";
    readerCheckTime = double(sscanf(input(promptReaderCheckTimeGet,'s'),'%f'));
    while(isempty(readerCheckTime) || ~isa(readerCheckTime,'numeric') || (readerCheckTime < 0))
        readerCheckTime = double(sscanf(input("Input Invalid. " + promptReaderCheckTimeGet,'s'),'%f'));
    end
end


function [xAnchor, yAnchor, zAnchor] = expAnchorGet(varargin)
    p = inputParser();
    p.addParameter('zPadding','Y');
    promptAnchorGet = "Enter the number of anchors: ";
    anchNumber = uint32(sscanf(input(promptAnchorGet, 's'), '%d'));
    while(isempty(anchNumber) || ~isa(anchNumber,'integer') || (anchNumber < 1))
        anchNumber = uint32(sscanf(input("Input Invalid. " + promptAnchorGet, 's'), '%d'));
    end
    
    %Intializing Anchor Position var
    xAnchor = zeros(1,anchNumber);
    yAnchor = zeros(1,anchNumber);
    zAnchor = zeros(1,anchNumber);
    uiwait(msgbox('Please confirm if you have completed position configuration for anchors',...
    'Anchor Setup Confirmation!!!!','warn'));
    
    p.parse(varargin{:});
    ZaxisZeroPadding = p.Results.zPadding;
    for i = 1:anchNumber
        xPrompt = sprintf("\t Enter x coordinate of anchor %d: ", i);
        xIn = double(sscanf(input(xPrompt,'s'),'%f'));
        while(isempty(xIn) || ~isa(xIn,'numeric'))
            xIn = double(sscanf(input("Input Invalid. " + xPrompt,'s'),'%f'));
        end
        xAnchor(i) = xIn;
        yPrompt = sprintf("\t Enter y coordinate of anchor %d: ", i);
        yIn = double(sscanf(input(yPrompt,'s'),'%f'));
        while(isempty(yIn) || ~isa(yIn,'numeric'))
            yIn = double(sscanf(input("Input Invalid. " + yPrompt,'s'),'%f'));
        end
        yAnchor(i) = yIn;
    end
    if(~strcmpi(ZaxisZeroPadding, 'Y'))
        for i = 1:anchNumber
            zPrompt = sprintf("\t Enter z coordinate of anchor %d: ", i);
            zIn = double(sscanf(input(zPrompt,'s'),'%f'));
            while(isempty(zIn) || ~isa(zIn,'numeric'))
                zIn = double(sscanf(input("Input Invalid. " + zPrompt,'s'),'%f'));
            end
            zAnchor(i) = zIn;
        end
    end
    
    posAnchor = zeros(1,2*length(xAnchor));
    posAnchor(1:2:end) = xAnchor;
    posAnchor(2:2:end) = yAnchor;
    fprintf("\n\n Position of archors in order " ); 
    disp(1:1:length(xAnchor));
    fprintf("\t(%0.2f,%0.2f)\n",posAnchor);
    % Ask the tester to double check anchor's location
    uiwait(msgbox(sprintf('Confirm Anchor Location: (x=%0.2f,y=%0.2f)\n', ...
        posAnchor),'Anchor Setup Confirmation','warn'));
end


function [mqttObj, mqttSub] = tagMqttSubscriptionInit(retry)
    try
        fprintf("[MQTT/Wi-Fi Backbone] Scanning the IP for tags in WLAN...\n");
        [hostIp, subnetMask] = hostIpParse();
        fprintf("[MQTT/Wi-Fi Backbone] Host ip: " + hostIp + "; Subnet Mask: " + subnetMask + "\n");
        [tagIp, tagMAC] = ipScan(hostIp, subnetMask);
        fprintf("[MQTT/Wi-Fi Backbone] Using the first found tag as the experiment object..." + "\n");

        % No tag has been identified raising concern
        if (length(tagIp) < 1)
            ME = MException('myComponent:inputErrorTag', ...
                 '[MQTT/Wi-Fi Backbone]No Tag found on WLAN');
            beep;
            throw(ME);  
        end

        fprintf("[MQTT/Wi-Fi Backbone] First tag ip found as: " + tagIp{1} + " MAC: " + tagMAC{1} + "\n");
        ipaddress = string(tagIp{1});
        tcp = "tcp://";
        tcp = tcp.append(ipaddress);
        link = "Tag/";
        link = link.append("+");
        link = link.append("/Uplink/Location");

        mqttObj = mqtt(tcp); 
        mqttSub = subscribe(mqttObj,link);
    catch ME
        if(strcmp(ME.identifier,'myComponent:inputErrorTag'))
            if (retry <= 3)
                uiwait(msgbox('Please check the if tags are on same WLAN and Retry',...
                'No Tag Found!!!!','warn'));
                retry = retry+1;
                fprintf("[MQTT/Wi-Fi Backbone] retry: %d \n", retry);
                [mqttObj, mqttSub] = tagMqttSubscriptionInit(retry);
            else
                 uiwait(msgbox('Maximum retry for tag discovery reached',...
                'No Tag Found!!!!','error'));
                 error(ME)
            end
        else
            rethrow(ME);
        end  
    end
end


function delayTimer(delayInSec)
    % UI function to display elapsed time in dots
    totalTasks = 50;
    period = delayInSec / totalTasks;
    T = timer('Period',period,...       %period
    'ExecutionMode','fixedRate',...     %{singleShot,fixedRate,fixedSpacing,fixedDelay}
    'BusyMode','drop',...               %{drop, error, queue}
    'TasksToExecute',totalTasks,...
    'StartDelay',0,...
    'TimerFcn',@(src,evt)fprintf(1,'.'),...
    'StartFcn',@(src,evt)fprintf(1,'\n'),...
    'StopFcn',@(src,evt)fprintf(1,'\n'),...
    'ErrorFcn',[]);
    start(T);
    pause(delayInSec);
end


function myCleanup()
    global expName scriptStatus
    fprintf('\n Close ALL \n');
    fclose("all");
    fprintf(expName + "\n");
    fprintf(scriptStatus + "\n");
    disp(pwd)
    if ~strcmp(scriptStatus,"FT")
        if ~contains(pwd,expName)
            cd(expName); 
        end
        delete("*.mat")
        delete("*.png")
    end
    cd ..
    clear;
end
