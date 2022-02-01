CENTERS=[1.16, 0.55];
RADII_TRUE_TRACK=0.45;

% Anchor Positions
X_ANCHOR = [0,    0,      2.33,   2.33];
Y_ANCHOR = [0,    1.11,   1.11,   0];

% LOS, no anchors blocked
% Buffer(0.1 m), LOS
radii_los_inner=0.35;
radii_los_outer=0.55;
figure(1);
set(gcf,'unit','normalized','position',[0.2,0.2,0.5,0.5]);
buffer_los_inner=viscircles(CENTERS, radii_los_inner, 'LineStyle', '--', 'LineWidth', 1, 'Color','m');
buffer_los_outer=viscircles(CENTERS, radii_los_outer, 'LineStyle', '--', 'LineWidth', 1, 'Color','m');
%True Position, in both LOS and NLOS
track_circle=viscircles(CENTERS, RADII_TRUE_TRACK, 'LineWidth',1,'LineStyle','-','Color','r');
hold on;

% Reading LOS text data directly
los_measurement = dlmread('Moving_Train_Raw.txt','',3,0);
X_LOS=los_measurement(:,1);
Y_LOS=los_measurement(:,2);
ans1_LOS=plot(X_LOS,Y_LOS,'b-');
%plotting the position of anchors
anch=plot(X_ANCHOR,Y_ANCHOR,'b^');
xlim([-.5,3.5]);
ylim([-.5,1.5]);
daspect([1 1 1]);
grid on;
legend([ans1_LOS, track_circle, buffer_los_inner, anch], 'Measured Position', 'True Position', 'Buffer (±0.1m)', 'Anchor');
title('Moving Train Measurement Perfect LOS Conditions');

xlabel('X coordinate (m)');
ylabel('Y coordinate (m)');
hold off;

% NLOS, blocking one anchor
% Buffer(0.2 m), NLOS
radii_nlos_inner=0.25;
radii_nlos_outer=0.65;
figure(2);
set(gcf,'unit','normalized','position',[0.2,0.2,0.5,0.5]);
buffer_nlos_inner=viscircles(CENTERS, radii_nlos_inner, 'LineStyle', '--', 'LineWidth', 1, 'Color','m');
buffer_nlos_outer=viscircles(CENTERS, radii_nlos_outer, 'LineStyle', '--', 'LineWidth', 1, 'Color','m');
%True Position, in both LOS and NLOS
track_circle=viscircles(CENTERS, RADII_TRUE_TRACK, 'LineWidth',1,'LineStyle','-','Color','r');
hold on;

% Reading NLOS text data directly
nlos_measurement = dlmread('NLOS_Moving_Train_1anchor.txt','',3,0);
X_NLOS=nlos_measurement(:,1);
Y_NLOS=nlos_measurement(:,2);
ans1_NLOS=plot(X_NLOS,Y_NLOS,'b-');
% plotting the position of anchors
x_unblocked_anch = X_ANCHOR;
y_unblocked_anch = Y_ANCHOR;
x_blocked_anch = x_unblocked_anch(3);
y_blocked_anch = y_unblocked_anch(3);
x_unblocked_anch(3) = [];
y_unblocked_anch(3) = [];
anch = plot(x_unblocked_anch,y_unblocked_anch,'b^');
bloced_anch = plot(x_blocked_anch, y_blocked_anch, 'r^');
xlim([-.5,3.5]);
ylim([-.5,1.5]);
daspect([1 1 1]);
grid on;
legend([ans1_NLOS, track_circle, buffer_nlos_inner, anch, bloced_anch], ...
    'Measured Position', 'True Position', 'Buffer (±0.2m)', 'Unblocked Anchor','Blocked Anchor');
title('Moving Train Measurement with One Anchor Blocked');
xlabel('X coordinate (m)');
ylabel('Y coordinate (m)');
hold off;