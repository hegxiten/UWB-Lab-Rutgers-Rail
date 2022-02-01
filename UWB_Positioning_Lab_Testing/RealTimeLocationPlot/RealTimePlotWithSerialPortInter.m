function RealTimePlotWithSerialPort()

%%Predefined values of variable starts
serialPort="COM8";
x_anch=[0,0,7.43,7.43];
y_anch=[0,7.77,7.77,0];
%%Predefined values of variable starts

%%Check if user wants to use predefined values
checkForPreDefined = input("Enter the serial port of paassive device to"...
                +"read data from (e.g COM8)",'s');

%%Predefined values of variable ends
%Getting serial port from the user
serialPort = input("Enter the serial port of paassive device to"...
                +"read data from (e.g COM8)",'s');
            
%Getting name of the experiment
expName = input("Enter the name of the experiment ",'s');
%Getting number of anchors
anchNumber = input("Enter the number of UWB anchors");
%Getting number of tags
tagNumber = input("Enter the number of UWB tags");


%Setting serial port to establish connection
s=serialport(serialPort,115200);



figure();
box on;
set(gcf,'unit','normalized','position',[0.2, 0.2, 0.5, 0.5]);
plot(x_anch, y_anch,z_anch,'r^');
axis([-10 10 -10 10 0 5]);
title(expName);
xlabel('X coordinate (m)');
ylabel('Y coordinate (m)');
daspect([1 1 1]);
grid on;
hold on;
while(1)
    data = readline(s);
    new = split(data,",");
    X=str2double(new(4));
    Y=str2double(new(5));
    check = geofencing(X,Y);
    if(check)
        disp("OUT OF ZONE")
    end
    plot(X,Y, 'b^');   
    %hold on
end

%Call to clean up function to close port 
cleanup = onCleanup(@()myCleanup(s));

end


function check = geofencing(X,Y)
check = false;
if ((X < 0) || (Y < 0)|| (X > 7.43)|| (Y>7.77))
   check=true; 
   disp("OUT OF THE ZONE"); 
end
end


function myCleanup(S)
disp('Port Close');
delete(S);
end
