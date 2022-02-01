
function Test

    x_anch=[0,0,2.33,2.33];
    y_anch=[0,1.11,1.11,0];
    X_TRUE = (0.22:0.29:2.25);
    Y_TRUE = repelem((0.55),length(X_TRUE));
    
    fid = fopen('myfile.txt');
    cleanup = onCleanup(@()myCleanup());
    figure();
    box on;
    set(gcf,'unit','normalized','position',[0.2, 0.2, 0.5, 0.5]);
    anch = plot(x_anch, y_anch, 'r^');
    
    axis([-0.5 4 -0.5 1.5]);
    daspect([1 1 1]);
    grid on
    hold on;
    count=0;
    while ~feof(fid)
        tline = fgetl(fid);
        check = size(tline);
        var=split(tline,",");
        expression = '[^\n]*PuTTY[^\n]*';
        matches = regexp(tline,expression,'match');
       if (isempty(matches) && (check(2)>10))
           X=str2double(var(4));
           Y=str2double(var(5));
           plot_measured=plot(X,Y, 'b^');
        display(count);
        count = count+1;
       end
        pause(0.05)
    end        
    fclose(fid);
    plot_true_pos = plot(X_TRUE, Y_TRUE, 'r.-','LineWidth',1);
    centers = [X_TRUE' Y_TRUE'];
    radii = repelem(0.1,8,1);
    buff=viscircles(centers,radii,'LineStyle','--','Color','m');
    l = legend([plot_true_pos,plot_measured,anch,buff],...
        'True Position','Measured Position','Anchor',...
    'Accuracy Buffer (±0.1m)');
    set(l, 'Location', 'southeast');
end    

function myCleanup()
disp('Close File');
fclose('all');
end


    
   