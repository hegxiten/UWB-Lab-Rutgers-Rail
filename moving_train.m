
%Buffer(-0.1 m)
centers=[1.16, 0.55];
radii=0.35;
buffer1=viscircles(centers,radii,'LineWidth',0.5,'LineStyle','--');
hold on

%Buffer(+0.1 m)
centers=[1.16, 0.55];
radii=0.55;
buffer2=viscircles(centers,radii,'LineWidth',0.5,'LineStyle','--');
hold on

%True Value
centers=[1.16, 0.55];
radii=0.45;
truevalue=viscircles(centers,radii,'LineWidth',0.5,'LineStyle','--');
hold on

%Measured Value from decawave LOS
num1=xlsread('moving_train1.xlsx');
X_LOS=num1(:,1);
Y_LOS=num1(:,2);
ans1_LOS=plot(X_LOS,Y_LOS,'b-')

%Measured Value from decawave NLOS(Anchor 3 blocked)
%num1=xlsread('NLOS_movingtrain_1anchor.xlsx');
%X_NLOS=num1(:,1);
%Y_NLOS=num1(:,2);
%ans1_NLOS=plot(X_NLOS,Y_NLOS,'b-')


%axis([0 3 0 3]);

%Anchor Positions

anchor1=plot(0,0,'^');
anchor2=plot(0,1.1,'^');
anchor3=plot(2.33,1.11,'^');
anchor4=plot(2.33,0,'^');

xlim([-.5,2.5]);
ylim([-.5,2.5]);

hold off


legend([ans1_LOS, truevalue, buffer1, buffer2,anchor1,anchor2,anchor3,anchor4], 'Measured value', 'True Value', 'Buffer(-0.1m)', 'Buffer(+0.1m)','Anchor1','Anchor2','Anchor3','Anchor4');
title('Moving train');
xlabel('Distance in meters');
ylabel('Distance in meters');

