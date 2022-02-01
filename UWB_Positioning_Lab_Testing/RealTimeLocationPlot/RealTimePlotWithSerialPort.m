function RealTimePlotWithSerialPort()


%Call to clean up function to close port 

%%Predefined values of variable starts
serialPort="COM8";
x_anch=[0,10,10,0];
y_anch=[0,0,10,10];
%%Predefined values of variable starts

s=serialport(serialPort,115200);
cleanup = onCleanup(@()myCleanup(s));
figure();
box on;
set(gcf,'unit','normalized','position',[0.2, 0.2, 0.5, 0.5]);
plot(x_anch, y_anch,'r^');
axis([-15 15 -15 15]);
title(" OUTDOOR 1");
xlabel('X coordinate (m)');
ylabel('Y coordinate (m)');
daspect([1 1 1]);
grid on;
hold on;
while(1)
    data = readline(s);
    disp(data)
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
