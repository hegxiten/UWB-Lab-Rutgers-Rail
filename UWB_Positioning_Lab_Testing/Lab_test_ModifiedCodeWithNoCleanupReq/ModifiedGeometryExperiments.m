%Ground truth
X_TRUE = [0.22:0.29:2.25];
Y_TRUE = repelem([0.55],length(X_TRUE));
%BUFFER_POS = [0.12, 0.45, 2.23, 0.2];

%Anchor postion for TagElevated,AnchorsElevated,SquareTopology%
x_anch_height=[0,0,2.33,2.33];
y_anch_height=[0,1.11,1.11,0];


GeoExp('EXP1',x_anch_height,y_anch_height,X_TRUE,Y_TRUE);
GeoExp('EXP3',x_anch_height,y_anch_height,X_TRUE,Y_TRUE);


function GeoExp(name,x_anch_pos,y_anch_pos,x_true,y_true)
    % %Anchor Positions  for height exp
    cleanup = onCleanup(@()myCleanup());
    cd (name)
    dinfo = dir('POS*.txt');
    filenames = {dinfo.name};
    x_tag_pos_avg=zeros(1,length(filenames));
    y_tag_pos_avg=zeros(1,length(filenames));
    x_tag_pos_std=zeros(1,length(filenames));
    y_tag_pos_std=zeros(1,length(filenames));
    for K = 1 : length(filenames)
        thisfile = filenames{K};
        display(thisfile);
        %read the raw file as matrix first row is ignored
		pos1 = readmatrix(thisfile);
        %extracted X and Y coordinates from the file 
		pos1 = pos1(:,4:5);
		pos1 = pos1(all(~isnan(pos1),2),:);
        avgPos1 = mean(pos1);
        stdPos1 = std(pos1);
        x_tag_pos_avg(1,K) = avgPos1(1,1);
        y_tag_pos_avg(1,K) = avgPos1(1,2);
        x_tag_pos_std(1,K) = stdPos1(1,1);
        y_tag_pos_std(1,K) = stdPos1(1,2);
    end

pos_plot(x_true, y_true, x_tag_pos_avg, y_tag_pos_avg, x_tag_pos_std,y_tag_pos_std,...
    x_anch_pos, y_anch_pos, name);
pos_errorbar(x_true, y_true, x_tag_pos_avg, y_tag_pos_avg, x_tag_pos_std,y_tag_pos_std,...
    x_anch_pos, y_anch_pos, name);
end


function pos_plot(x_true, y_true, x_measure, y_measure, x_std, y_std, ...
    x_anch, y_anch, title_name)
    % function call to plot according to different data
    % NO NEED TO COMMENT/UNCOMMENT
    % Display plot while done
    
    % To be used for blockage scenario
    BLOCKAGE1_POS = [0.1, 0.98,0.02,0.3];
    BLOCKAGE2_POS = [2.2, 0.98,0.02,0.3];
    
    figure();
    box on;
    set(gcf,'unit','normalized','position',[0.2, 0.2, 0.5, 0.5]);
    hold on;
    % Plot the dummy handles for legend
    std_1 = plot(nan, nan, 'bo', 'MarkerFaceColor','b');
    %buff = plot(nan, nan, 'LineStyle','--', 'Color','m');

    % Plot the std. deviation for all data points of geo1
    for i = 1:1:length(x_true)
        theta = 0 : 0.01 : 2*pi;
        xcenter = x_measure(i);
        ycenter = y_measure(i);
        xradius = x_std(i);
        yradius = y_std(i);
        x_s = xradius * cos(theta) + xcenter;
        y_s = yradius * sin(theta) + ycenter;
        h = fill(x_s,y_s,'b','facealpha',0.3);
        hold on
    end

    % Plot the connection from truth to measurements
    for i = 1:1:length(x_true)
        quiver(x_true(i), y_true(i), x_measure(i)-x_true(i), y_measure(i)-y_true(i),'color','k','LineStyle',':','LineWidth',0.3);
        hold on
    end

    % Plot the anchor positions
    anch = plot(x_anch, y_anch, 'b^');
    % Plot the buffer (+-10cm) for decawave
    %rectangle('Position', buffer_pos, 'LineStyle',':', 'EdgeColor','m', 'Curvature', 1,'LineWidth',0.3);
    centers = [x_true' y_true'];
    radii = repelem(0.1,8,1);
    buff=viscircles(centers,radii,'LineStyle','--','Color','m');
    
    if(contains(title_name,"Blocked"))
        rectangle('Position',BLOCKAGE1_POS, 'EdgeColor','k', 'FaceColor', 'k', 'Curvature', 0.2,'LineWidth',0.3);
        rectangle('Position',BLOCKAGE2_POS, 'EdgeColor','k', 'FaceColor', 'k', 'Curvature', 0.2,'LineWidth',0.3);
    end
    % Plot the true positions of tags
    plot_true_pos = plot(x_true, y_true, 'r.-','LineWidth',1);
    % Plot the measured positions of tags
    plot_measured = plot(x_measure, y_measure,'b-','LineWidth',2);
    axis([-0.5 4 -0.5 1.5]);
    daspect([1 1 1]);
    grid on;
    l = legend([plot_true_pos,plot_measured,std_1,anch,buff],...
        'True Position','Measured Position','Standard Deviation (Oval)',...
        'Anchor', 'Accuracy Buffer (±0.1m)');
    set(l, 'Location', 'southeast');
    title(title_name);
    xlabel('X coordinate (m)');
    ylabel('Y coordinate (m)');
    hold off;
    legend boxon

end

function pos_errorbar(x_true, y_true, x_measure, y_measure, x_std, y_std, ...
    x_anch, y_anch, title_name)
    % function call to plot according to different data, using errorbar
    % NO NEED TO COMMENT/UNCOMMENT
    % Display plot while done
    
    % To be used for blockage scenario
    BLOCKAGE1_POS = [0.1, 0.98,0.02,0.3];
    BLOCKAGE2_POS = [2.2, 0.98,0.02,0.3];
      
    
    figure();
    set(gcf,'unit','normalized','position',[0.2, 0.2, 0.5, 0.5]);
    e1 = errorbar(x_measure, y_measure, y_std, y_std, x_std, x_std,...
        'Marker','o','LineStyle','-','LineWidth',2);
    hold on;
    % Plot the anchor positions
    anch = plot(x_anch, y_anch, 'b^');
    % Plot the dummy handles for legend
    %buff = plot(nan, nan, 'LineStyle','--', 'Color','m','LineWidth',0.3);
    % replot in a zoomed-in manner
    %rectangle('Position', buffer_pos, 'LineStyle',':', 'EdgeColor','m', 'Curvature', 1,'LineWidth',0.3);
    centers = [x_true' y_true'];
    radii = repelem(0.1,8,1);
    buff=viscircles(centers,radii,'LineStyle','--','Color','m');
    
    if(contains(title_name,"Blocked"))
        rectangle('Position',BLOCKAGE1_POS, 'EdgeColor','k', 'FaceColor', 'k', 'Curvature', 0.2,'LineWidth',0.3);
        rectangle('Position',BLOCKAGE2_POS, 'EdgeColor','k', 'FaceColor', 'k', 'Curvature', 0.2,'LineWidth',0.3);
    end
    
    true_pos = plot(x_true, y_true, 'r.-','LineWidth',1);
    % Plot the connection from truth to measurements
    for i = 1:1:length(x_true)
        quiver(x_true(i), y_true(i), x_measure(i)-x_true(i), y_measure(i)-y_true(i),'color','k','LineStyle',':','LineWidth',0.3);
        hold on
    end
    daspect([1 1 1]);
    grid on;
    l = legend([true_pos,e1,buff,anch],'True Position','Measured Position','Accuracy Buffer (±0.1m)','Anchor');
    set(l, 'Location', 'southeast');
    axis([-0.5 4 -0.5 1.5]);
    title(title_name);
    xlabel('X coordinate (m)');
    ylabel('Y coordinate (m)');
    
end

function myCleanup()
disp('Close Files');
fclose('all');
cd ..
end