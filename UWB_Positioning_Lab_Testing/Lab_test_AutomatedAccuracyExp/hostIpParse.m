% function parses the IP and subnet mask of the colloctor's machine 
function [hostIp, subnetMask] = hostIpParse()
    hostIp = strings;
    subnetMask = strings;
    if(ispc)
        [~, ipOut] = system('ipconfig');
        ipOutLines = splitlines(ipOut);
        for i=1:1:length(ipOutLines)
           if(contains(ipOutLines{i}, 'Wireless LAN adapter Wi-Fi:'))
               startIdx = i + 1;
               k = startIdx;
               while(k<=length(ipOutLines))
                   k = k + 1;
                   if(isempty(ipOutLines{k}))
                       endIdx = k;
                       break
                   end
               end
               for j=startIdx:1:endIdx
                   if(contains(ipOutLines{j}, 'IPv4 Address'))
                       hostIp = regexp(ipOutLines{j},'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}','match');
                   end
                   if(contains(ipOutLines{j}, 'Subnet Mask'))
                       subnetMask = regexp(ipOutLines{j},'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}','match');
                   end
               end
               break
           end
        end
        
    elseif(ismac)
        [~, ipOut] = system('ifconfig');
        ipOutLines = splitlines(ipOut);
        for i=1:1:length(ipOutLines)
           if(contains(ipOutLines{i}, 'en0'))
               k = i + 1;
               while(k<=length(ipOutLines))
                   k = k + 1;
                   if(contains(ipOutLines{k}, 'inet') && ~contains(ipOutLines{k}, 'inet6'))
                       hostIpRaw = regexp(ipOutLines{k},'inet \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}','match');
                       hostIp = regexp(hostIpRaw{1},'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}','match');
                       subnetMaskRaw = regexp(ipOutLines{k},'([0-9A-Fa-f]{8})','match');
                       field_1 = num2str(hex2dec(subnetMaskRaw{1}(1:2)));
                       field_2 = num2str(hex2dec(subnetMaskRaw{1}(3:4)));
                       field_3 = num2str(hex2dec(subnetMaskRaw{1}(5:6)));
                       field_4 = num2str(hex2dec(subnetMaskRaw{1}(7:8)));
                       subnetMask = strcat({field_1},{'.'},{field_2},{'.'},...
                           {field_3},{'.'},{field_4});
                   break
                   end
               end
               break
           end
        end
    
    elseif(isunix)
        error('MATLAB runtime scanner on unix is not developped yet!')
    end
end