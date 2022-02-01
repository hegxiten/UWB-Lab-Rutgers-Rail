function ErrorDistributionCrossComp()
cleanup = onCleanup(@()myCleanup());
dirName = input("Enter the dir structure name for which you "+...
           "plot data ",'s');       
CrossCompare(dirName);

end

function CrossCompare(dirName)
dirName = dirName+"*";
dinfo = dir(dirName);
filenames = {dinfo.name};
figure(1);
subplot(2,3,1);
box on;
subplot(2,3,2);
box on;
subplot(2,3,3);
box on;
subplot(2,3,4);
box on;
subplot(2,3,5);
box on;
subplot(2,3,6);
box on;
for i=1:length(filenames)
    load(filenames(i)+"/Error","Xerror", "Yerror");
    figure(1);
    subplot(2,3,1);
    ecdf(Xerror);
    hold on;
    subplot(2,3,2);
    plot(linspace(min(Xerror),max(Xerror)),evcdf(linspace(min(Xerror)...
        ,max(Xerror)),mean(Xerror),std(Xerror)),"+-");
    hold on;
    subplot(2,3,3);
    plot(linspace(min(abs(Xerror)),max(abs(Xerror))),evcdf(linspace(min(abs(Xerror))...
        ,max(abs(Xerror))),mean(abs(Xerror)),std(abs(Xerror))),"*-");
    hold on;
    subplot(2,3,4);
    ecdf(Yerror);
    hold on;
    subplot(2,3,5);
    plot(linspace(min(Yerror),max(Yerror)),evcdf(linspace(min(Yerror)...
        ,max(Yerror)),mean(Yerror),std(Yerror)),"+-");
    hold on;
    subplot(2,3,6);
    plot(linspace(min(abs(Yerror)),max(abs(Yerror))),evcdf(linspace(min(abs(Yerror))...
        ,max(abs(Yerror))),mean(abs(Yerror)),std(abs(Yerror))),"*-");
    hold on;
end
figure(1);
subplot(2,3,1);
grid on;
legend((filenames),"location","Southeast","Linewidth",1.5);
title("Empherical CDF for X axis error");
xlabel("Error for X axis (m)");
ylabel("Probability");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;

subplot(2,3,2);
grid on;
legend((filenames),"location","Southeast","Linewidth",1.5);
title("Theoritical CDF for X axis error");
xlabel("Error for X axis (m)");
ylabel("Probability");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;

subplot(2,3,3);
grid on;
legend((filenames),"location","Southeast","Linewidth",1.5);
title("Theoritical CDF for X axis absolute error");
xlabel("Error for X axis (m)");
ylabel("Probability");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;

subplot(2,3,4);
grid on;
legend((filenames),"location","Southeast","Linewidth",1.5);
title("Empherical CDF for Y axis error");
xlabel("Error for Y axis (m)");
ylabel("Probability");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;

subplot(2,3,5);
grid on;
legend((filenames),"location","Southeast","Linewidth",1.5);
title("Theoritical CDF for Y axis error");
xlabel("Error for Y axis (m)");
ylabel("Probability");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;

subplot(2,3,6);
grid on;
legend((filenames),"location","Southeast","Linewidth",1.5);
title("Theoritical CDF for Y axis absolute error");
xlabel("Error for Y axis (m)");
ylabel("Probability");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;


end

function myCleanup()
fprintf('\n Close ALL \n');
fclose("all");
clear;
end