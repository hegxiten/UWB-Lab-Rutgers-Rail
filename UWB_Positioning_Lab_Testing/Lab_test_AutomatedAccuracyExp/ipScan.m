% Scan the ip address of tags in the same WLAN network
% Dependency: nmap available at https://nmap.org/download.html
function [tagIp, tagMAC] = ipScan(hostIp, subnetMask)
    tagIp = {};
    tagMAC = {};
    
    subnetSegment = netSegParse(hostIp, subnetMask);
    if(ispc)
        % Nmap is installed with administrator privilege
        [stat, nmapOut] = system(char(strcat('nmap -sP',{' '},subnetSegment,...
            {' '},{'--exclude'},{' '},hostIp)));
    elseif(ismac)
        % set proper env to execute nmap
        setenv('PATH', [getenv('PATH') ':/usr/local/bin:/usr/bin:/bin']);
        % MAC address won't show without sudo
        % Password needed for authentication
        fprintf("[Wi-Fi Backbone] If suspends, enter sudo password and press enter: \n")
        [stat, nmapOut] = system(char(strcat('sudo nmap -sP',{' '},subnetSegment,...
            {' '},{'--exclude'},{' '},hostIp)));
        
    elseif(isunix)
        error('MATLAB runtime scanner on unix is not developped yet!')
    end
    
    %nmap is not configured correctly terminating program with an error
    if (stat ==1)
        uiwait(msgbox('Please check nmap configuration either it is not installed or command path is not set',...
        'nmap Error!!!!','error'));
        error("nmap configuration error")
    end
    
    nmapOutLines = splitlines(nmapOut);
    trimmedNmapOut = nmapOutLines(2:end-2);
    try
        for i = 3:1:length(trimmedNmapOut)
            detectedIdxCell = regexp(trimmedNmapOut(i), 'Raspberry Pi');
            if(~isempty(detectedIdxCell{1}))
                detectedIp = regexp(trimmedNmapOut(i-2),'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}','match');
                detectedMac = regexp(trimmedNmapOut(i),'([0-9A-F]{2}:){5}[0-9A-F]{2}','match');
                tagIp(length(tagIp)+1) = detectedIp;
                tagMAC(length(tagMAC)+1) = detectedMac;
            end
        end
    catch ME
        disp(nmapOutLines);
        disp(size(nmapOutLines));
        rethrow(ME);
    end
end

function netSegment = netSegParse(ip, subnetMask)
    % Extract the net IP segment as ***.***.***.***/**
    ipStr = split(ip, '.');
    maskStr = split(subnetMask, '.');
    ipDec = cellfun(@str2num, ipStr);
    maskDec = cellfun(@str2num, maskStr);
    ipSegmentDec = reshape(bitand(ipDec, maskDec),[size(ipDec,2),size(ipDec,1)]);
    ipSegmentStr = strjoin(arrayfun(@num2str, ipSegmentDec, 'UniformOutput',false),'.');
    slashLength = length(strfind(reshape(dec2bin(maskDec),[1,32]),'1'));
    % Converting IP + mask format to IP/24 format as input to nmap
    netSegment = strcat(ipSegmentStr, {'/'},num2str(slashLength));
end