%Ground truth
for v = 0.22:0.29:2.25
    a1=plot(v,0.55,'*');
    hold on
end

%for v = 0.32:0.29:2.35
   % a2=plot(v,0.65,'+');
    %hold on
%end
%for v = 0.12:0.29:2.15
  %  a3=plot(v,0.45,'^');
   % hold on
%end
%Plot the buffer (+-10cm) for decawave
rectangle('Position',[0.12 0.45 2.5 0.20]);
%Anchor Positions  for square geometry
%anchor1=plot(0,0,'^');
%anchor2=plot(0,1.1,'^');
%anchor3=plot(2.33,1.11,'^');
%anchor4=plot(2.33,0,'^');

%Anchor Positions  for Triangle geometry
anchor1=plot(0,0,'^');
anchor2=plot(1.143,0,'^');
anchor3=plot(2.33,0,'^');
anchor4=plot(1.143,1.168,'^');

%Anchor Positions on one side data(Slide 11)
%anchor1=plot(0,0,'^');
%anchor2=plot(0.9,0,'^');
%anchor3=plot(2.33,0,'^');
%anchor4=plot(1.8,-0.3,'^');


%Anchor position for anchors on one side with two anchors further away Slide 13
%anchor1=plot(0,0,'^');
%anchor2=plot(0.9,-0.3,'^');
%anchor3=plot(2.33,0,'^');
%anchor4=plot(1.8,-0.3,'^');


%All values below are measured values from decawave

%x=[0.20,0.45,0.84,1.12,1.48,1.70,2.0,2.35];%Effect of anchor height(Slide 7) 2nd plot data
%y=[0.56,0.60,0.53,0.57,0.57,0.43,0.42,0.53];

%x=[0.22,0.53,0.82,1.08,1.39,1.72,2.07,2.50];;%Square geometry data(Slide 9)
%y=[0.55,0.53,0.56,0.56,0.57,0.68,0.72,0.77];
%x_std=[0.025,0.024,0.022,0.022,0.025,0.013,0.022,0.038];
%y_std=[0.016,0.015,0.010,0.009,0.013,0.019,0.026,0.291];

x1=[0.22,0.53,0.82,1.08,1.39,1.72,2.07,2.50];%Tringle geometry data(Slide 10)
y1=[0.55,0.53,0.56,0.56,0.57,0.62,0.65,0.57];
%x1_std=[0.028,0.012,0.010,0.021,0.010,0.011,0.017,0.024];
%y1_std=[0.018,0.012,0.025,0.046,0.032,0.026,0.015,0.013];

%x3=[0.26,0.55,0.84,1.10,1.41,1.68,1.93,2.29];%All anchors on one side data(Slide 11)
%y3=[0.30,0.25,0.24,0.21,0.44,0.35,0.36,0.13];

%x3_std=[0.013,0.011,0.015,0.017,0.016,0.011,0.012,0.020];%Std. deviation for slide 11 exp
%y3_std=[0.059,0.049,0.073,0.062,0.041,0.036,0.040,0.046];

%x4=[0.23,0.55,0.79,1.12,1.39,1.65,1.93,2.25];%All anchors on one side with two anchors further away Slide 13
%y4=[0.38,0.40,0.46,0.49,0.43,0.37,0.38,0.28];

%x4_std=[0.021,0.016,0.023,0.031,0.014,0.027,0.022,0.018];%Std. deviation for slide 13 exp
%y4_std=[0.043,0.041,0.042,0.046,0.030,0.042,0.070,0.075];

%Plot the std. Deviation for all data points
for i = 1:1:8
    theta = 0 : 0.01 : 2*pi;
    xcenter=x4(i);
    ycenter=y4(i);
    xradius=x4_std(i);
    yradius=y4_std(i);
    x_s = xradius * cos(theta) + xcenter;
    y_s = yradius * sin(theta) + ycenter;
    
    %h = fill(x_s,y_s,'b');
% Choose a number between 0 (invisible) and 1 (opaque) for facealpha.  
    %set(h,'facealpha',.7)
   %a5=plot(x_s, y_s);
    hold on
end


a4=plot(x1,y1,'o');
xlim([-.5,3]);
ylim([-.5,2]);
%axis([0 3 0 1.1]);
legend([a1,a4,anchor1,anchor2,anchor3,anchor4],'True value','Measured value',',anchor1','anchor2','anchor3','anchor4');
title('Tringle Geometry');
xlabel('Distance in meters');
ylabel('Distance in meters');





