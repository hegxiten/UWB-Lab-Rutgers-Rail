% ------------ Data input ------------
global X_SCALE Y_SCALE ACCURACY_BUFFER 
global BLOCKAGE_POS BUFFER_POS BUFFER_POS_scaled
global X_ANCH Y_ANCH X_ANCH_ADDITIONAL Y_ANCH_ADDITIONAL
X_SCALE = 1/8;          % the X scale ratio used for this miniature experiment
Y_SCALE = 1/8;          % the Y scale ratio used for this miniature experiment
ACCURACY_BUFFER = 0.1;  % accuracy buffer provided by Decawave

% Position of metal blockage (rectangular shape) used in the experiment
% Four-element vector of the form [x y w h]: 
% x, y of lower-left corner;
% w, h - width and height of the rectangle
BLOCKAGE_POS = [0.7, 0.65, 0.6, 0.02];

% Ground truth values of tag positions, X and Y
Y_TAG = 1.4;    % all the tags have the same ground truth Y value
X_TRUE = [0,      0.25,   0.5,    0.75,   1,      1.25,   1.5,    1.75];
Y_TRUE = repelem(Y_TAG, 8);


% factual buffer position, unscaled
BUFFER_POS = [
    min(X_TRUE) - ACCURACY_BUFFER, ...
    min(Y_TRUE) - ACCURACY_BUFFER, ...
    min(X_TRUE) - ACCURACY_BUFFER + (max(X_TRUE) - min(X_TRUE)) + ACCURACY_BUFFER*3, ...
    2 * ACCURACY_BUFFER];
% scaled buffer position, rectangle
% Four-element vector of the form [x y w h]: 
% x, y of lower-left corner;
% w, h - width and height of the rectangle
BUFFER_POS_scaled = [
    min(X_TRUE) - ACCURACY_BUFFER*X_SCALE, ...
    min(Y_TRUE) - ACCURACY_BUFFER*Y_SCALE, ...
    min(X_TRUE) - ACCURACY_BUFFER*X_SCALE + (max(X_TRUE) - min(X_TRUE)) + ACCURACY_BUFFER*X_SCALE*3, ...
    2 * ACCURACY_BUFFER*Y_SCALE];

% measured positions of tags with 5 anchors: experiment 1
[x_exp1,y_exp1,x_exp1_std,y_exp1_std] = getData("Five_anchors");

% measured positions of tags with 6 anchors: experiment 2
% experiment 2: added one additional anchor to compensate the blockage
% TODO: implement a datapreprocessing pipeline to avoid hard coded data
[x_exp2,y_exp2,x_exp2_std,y_exp2_std] = getData("Six_anchors");


% Calculate the scaled value for measured Y values of both experiments
y_exp1_scaled_delta = (Y_TRUE - y_exp1)*Y_SCALE + Y_TRUE;
y_exp2_scaled_delta = (Y_TRUE - y_exp2)*Y_SCALE + Y_TRUE;
% Anchor position for experiment 1
X_ANCH = [0,  1,  2,  0,      2];
Y_ANCH = [0,  0,  0,  2.8,    2.8];
% Anchor position for experiment 2, one additional anchor in red
X_ANCH_ADDITIONAL = [1];
Y_ANCH_ADDITIONAL = [0.7];

% ------------ Plotting Raw ------------
figure();
set(gcf,'unit','normalized','position',[0.2, 0.2, 0.5, 0.5]);
subplot(1,2,1);
% Experiment 1, 5 anchors
plotData(gca, x_exp1, y_exp1, x_exp1_std, y_exp1_std, X_TRUE, Y_TRUE,...
    false, 'Side Blockage NLOS Conditions, 5 Fixed Anchors',...
    'north', true, [-0.5 2.5 -0.5 3]);
subplot(1,2,2);
% Experiment 2, 6 anchors
plotData(gca, x_exp2, y_exp2, x_exp2_std, y_exp2_std, X_TRUE, Y_TRUE,...
    true, 'Side Blockage NLOS Conditions, 5 Fixed Anchors and 1 Relaying Anchor',...
    'north', true, [-0.5 2.5 -0.5 3]);

% ------------ Plotting Zoomed ------------
figure()
subplot(2,1,1);
set(gcf,'unit','normalized','position',[0.2, 0.2, 0.5, 0.5]);
% Experiment 1, 5 anchors, zoomed in
plotData(gca, x_exp1, y_exp1, x_exp1_std, y_exp1_std, X_TRUE, Y_TRUE,...
    false, 'Side Blockage NLOS Conditions, 5 Fixed Anchors (Zoomed in)',...
    'northeast', true, [-0.5 2.5 1.2 1.7]);
% Experiment 2, 6 anchors, zoomed in
subplot(2,1,2);
plotData(gca, x_exp2, y_exp2, x_exp2_std, y_exp2_std, X_TRUE, Y_TRUE,...
    true, 'Side Blockage NLOS Conditions, 5 Fixed Anchors and 1 Relaying Anchor (Zoomed in)',...
    'northeast', true, [-0.5 2.5 1.2 1.7]);

% ------------ Plotting Scaled ------------
% Y-axis deviation is scaled, X-axis devaition is not scaled
x_scale = 20;
y_scale = 8;
figure();
set(gcf,'unit','normalized','position',[0.2, 0.2, 0.5, 0.5]);
subplot(1,2,1);
% Experiment 1, 5 anchors
plotDataScaled(gca, x_exp1, y_exp1_scaled_delta, X_TRUE, Y_TRUE, x_scale, y_scale, ...
    false, 'Side Blockage NLOS Conditions, 5 Fixed Anchors (Scaled)',...
    'north', [-0.5 2.5 -0.5 3]);
% Experiment 2, 6 anchors
subplot(1,2,2);
plotDataScaled(gca, x_exp2, y_exp2_scaled_delta, X_TRUE, Y_TRUE, x_scale, y_scale, ...
    true, 'Side Blockage NLOS Conditions, 5 Fixed Anchors and 1 Relaying Anchor (Scaled)',...
    'north', [-0.5 2.5 -0.5 3]);


function [x_tag_pos_avg,y_tag_pos_avg,x_tag_pos_std,y_tag_pos_std]=getData(name)
    % Anchor positions for geofencing exp
    disp(name)
    cd (name)
    dinfo = dir('pos*.txt');
    filenames = {dinfo.name};
    x_tag_pos_avg=zeros(1,length(filenames));
    y_tag_pos_avg=zeros(1,length(filenames));
    x_tag_pos_std=zeros(1,length(filenames));
    y_tag_pos_std=zeros(1,length(filenames));
    for K = 1 : length(filenames)
        thisfile = filenames{K};
        cleanData(thisfile)
        pos1 = readtable('temp.txt');
        pos1 = pos1(:,1:2);
        pos1 = table2array(pos1);
        pos1 = pos1(any(~isnan(pos1),2),:);
        avgPos1 = mean(pos1);
        stdPos1 = std(pos1);
        x_tag_pos_avg(1,K) = avgPos1(1,1);
        y_tag_pos_avg(1,K) = avgPos1(1,2);
        x_tag_pos_std(1,K) = stdPos1(1,1);
        y_tag_pos_std(1,K) = stdPos1(1,2);
    end
cd ..
end

% This function cleans the raw data obtained from the UWB devices. 
% Here we are reading the file line by line.
% Lines with "POS" along with postion data are removed and other lines are 
% writtern into temp file.
function cleanData(filename)
    disp(filename)
    fid = fopen(filename);
    fid1 = fopen('temp.txt','wt');
    % regexp is used with match feature to detect lines with "POS" 
    % in some files there are lines with POS in b/w data which create issue 
    % while processing   
    while ~feof(fid)
        tline = fgetl(fid);
        expression = '[^\n]*POS[^\n]*';
        matches = regexp(tline,expression,'match');
        if (isempty(matches ))
            fwrite(fid1,tline);
            fprintf(fid1,'\n');
        end
    end
    fclose(fid);
    fclose(fid1); 
end

% This function plots the measurement data without scaling ratio. 
% Options: 
% hasRelayingAnchors: true/false - if plots the relaying anchor
% isErrorBar: true/false - if plots the standard deviation in errorbar
%   style or oval style
% axisLimitsArray: 4-element array showing X-Y axis limits
function plotData(ax, xTag, yTag, xTagStd, yTagStd, X_TRUE, Y_TRUE,...
    hasRelayingAnchors, plotTitle, legendPos, isErrorBar, axisLimitsArray)
    % ------------ Plotting ------------
    hold on;
    % Plot the std. deviation for all data points
    if isErrorBar
        e = errorbar(xTag, yTag, yTagStd, yTagStd, xTagStd, xTagStd,...
            'Marker','o','LineStyle','-','LineWidth',1, 'Color', 'b');
    else
        std = plot(nan, nan, 'bo', 'MarkerFaceColor','b');
        for i = 1:1:length(xTag)
            theta = 0 : 0.01 : 2*pi;
            xcenter = xTag(i);
            ycenter = yTag(i);
            xradius = xTagStd(i);
            yradius = yTagStd(i);
            x_s = xradius * cos(theta) + xcenter;
            y_s = yradius * sin(theta) + ycenter;
            h = fill(x_s,y_s,'b','facealpha',0.3);
            hold on
        end
    end
    % Plot the dummy handles for the legend
    buff = plot(nan, nan, 'LineStyle','-.', 'Color',[.61 .51 .74]); % purple
    block = plot(nan, nan, 'ks', 'MarkerFaceColor','k');

    % Plot the connection from truth to measurements
    for i = 1:1:length(xTag)
        quiver(X_TRUE(i), Y_TRUE(i), xTag(i)-X_TRUE(i), yTag(i)-Y_TRUE(i),...
            'color','k','LineStyle',':','LineWidth',0.3);
        hold on
    end
    global X_ANCH Y_ANCH BUFFER_POS BLOCKAGE_POS X_ANCH_ADDITIONAL Y_ANCH_ADDITIONAL
    % Plot the anchor positions
    anch = plot(X_ANCH,Y_ANCH,'b^');
    if hasRelayingAnchors
        % Plot the added relaying anchor
        anch_add = plot(X_ANCH_ADDITIONAL, Y_ANCH_ADDITIONAL,'r^');
    end
    % Plot the buffer (+-10cm) for decawave
    rectangle('Position',BUFFER_POS, 'LineStyle','--', 'EdgeColor','m', ...
        'Curvature', 1,'LineWidth',0.3);
    % Plot the blockage
    rectangle('Position',BLOCKAGE_POS, 'EdgeColor','k', 'FaceColor', 'k', ...
        'Curvature', 0.2,'LineWidth',0.3);
    % Plot the true positions of tags
    true_pos = plot(X_TRUE,Y_TRUE,'r*-','LineWidth',1);
    % Plot the measured positions of tags
    measured = plot(xTag,yTag,'b.-.','LineWidth',1);
    axis(axisLimitsArray);
    daspect([1 1 1]);
    grid on;
    if isErrorBar
        if ~hasRelayingAnchors
            l = legend([true_pos,e,anch,buff,block],...
            'True Position','Measured Position',...
            'Fixed Anchors', 'Accuracy Buffer(0.1m)', 'Blockage');
        else
            l = legend([true_pos,e,anch,anch_add,buff,block],...
            'True Position','Measured Position',...
            'Fixed Anchors', 'Relaying Anchor(s)', 'Accuracy Buffer(0.1m)',...
            'Blockage');
        end
    else
        if ~hasRelayingAnchors
            l = legend([true_pos,measured,buff,anch,block],...
            'True Position','Measured Position','Accuracy Buffer(0.1m)',...
            'Fixed Anchors', 'Blockage');
        else
            l = legend([true_pos,measured,buff,anch,anch_add,block],...
            'True Position','Measured Position','Accuracy Buffer(0.1m)',...
            'Fixed Anchors', 'Relaying Anchor(s)','Blockage');
        end
    end
    set(l, 'Location', legendPos);
    title(plotTitle);
    xlabel('X coordinate (m)');
    ylabel('Y coordinate (m)');
    hold off;
end

% This function plots the measurement data with scaling ratio.
% Options: 
% hasRelayingAnchors: true/false - if plots the relaying anchor
% isErrorBar: true/false - if plots the standard deviation in errorbar
%   style or oval style
% axisLimitsArray: 4-element array showing X-Y axis limits
function plotDataScaled(ax, xTag, yTag, X_TRUE, Y_TRUE, x_scale, y_scale,...
    hasRelayingAnchors, plotTitle, legendPos, axisLimitsArray)
    % ------------ Plotting ------------
    hold on;
    % Plot the dummy handles for the legend
    block = plot(nan, nan, 'ks', 'MarkerFaceColor','k');
    % Plot the connection from truth to measurements
    for i = 1:1:length(xTag)
        quiver(X_TRUE(i), Y_TRUE(i), xTag(i)-X_TRUE(i), yTag(i)-Y_TRUE(i),...
            'color','k','LineStyle',':','LineWidth',0.3);
        hold on
    end
    global X_ANCH Y_ANCH BUFFER_POS BLOCKAGE_POS X_ANCH_ADDITIONAL Y_ANCH_ADDITIONAL
    % Plot the anchor positions
    anch = plot(X_ANCH,Y_ANCH,'b^');
    if hasRelayingAnchors
        % Plot the added relaying anchor
        anch_add = plot(X_ANCH_ADDITIONAL, Y_ANCH_ADDITIONAL,'r^');
    end
    % Plot the blockage
    rectangle('Position',BLOCKAGE_POS, 'EdgeColor','k', 'FaceColor', 'k', ...
        'Curvature', 0.2,'LineWidth',0.3);
    % Plot the true positions of tags
    true_pos = plot(X_TRUE,Y_TRUE,'r*-','LineWidth',1);
    % Plot the measured positions of tags
    measured = plot(xTag,yTag,'b.-','LineWidth',1);
    axis(axisLimitsArray);
    daspect([1 1 1]);
    grid on;
    if ~hasRelayingAnchors
        l = legend([true_pos,measured,anch,block],...
        'True Position','Measured Position (Delta-Y Scaled)',...
        'Fixed Anchors', 'Blockage');
    else
        l = legend([true_pos,measured,anch,anch_add,block],...
        'True Position','Measured Position (Delta-Y Scaled)',...
        'Fixed Anchors', 'Relaying Anchor(s)','Blockage');
    end
    set(l, 'Location', legendPos);
    title(plotTitle);
    xlabel('X coordinate (m)');
    ylabel('Y coordinate (m)');
    xt=arrayfun(@num2str,get(gca,'xtick')*x_scale,'un',0);
    yt=arrayfun(@num2str,get(gca,'ytick')*y_scale,'un',0);
    set(gca,'xticklabel',xt,'yticklabel',yt);
    hold off;
end
