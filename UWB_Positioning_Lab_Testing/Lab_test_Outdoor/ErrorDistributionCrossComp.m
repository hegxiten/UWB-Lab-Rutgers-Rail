function ErrorDistributionCrossComp()
cleanup = onCleanup(@()myCleanup());
% dirName = input("Enter the dir structure name for which you "+...
%            "plot data ",'s');       
CrossCompare();

end

function CrossCompare()
% dirName = dirName+"*";
% dinfo = dir(dirName);
% filenames = {dinfo.name};
filenames = ["OUTDOOR4(1010)","OUTDOOR5(2020)","OUTDOOR6(3020)","OUTDOOR7(3010)"];
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
% disp(dinfo);
for i=1:length(filenames)
    load(filenames(i)+"/Error","Xerror", "Yerror");
    figure(1);
    subplot(2,3,1);
    [f1,x1] = ecdf(Xerror);
    plot(x1, f1, 'linewidth', 1.5);
    hold on;
    subplot(2,3,2);
    plot(linspace(min(Xerror),max(Xerror)),evcdf(linspace(min(Xerror)...
        ,max(Xerror)),mean(Xerror),std(Xerror)),"-",'linewidth', 1.5);
    hold on;
    subplot(2,3,3);
    plot(linspace(min(abs(Xerror)),max(abs(Xerror))),evcdf(linspace(min(abs(Xerror))...
        ,max(abs(Xerror))),mean(abs(Xerror)),std(abs(Xerror))),"-",'linewidth', 1.5);
    hold on;
    subplot(2,3,4);
    [f1,x1] = ecdf(Yerror);
    plot(x1, f1, 'linewidth', 1.5);
    hold on;
    subplot(2,3,5);
    plot(linspace(min(Yerror),max(Yerror)),evcdf(linspace(min(Yerror)...
        ,max(Yerror)),mean(Yerror),std(Yerror)),"-",'linewidth', 1.5);
    hold on;
    subplot(2,3,6);
    plot(linspace(min(abs(Yerror)),max(abs(Yerror))),evcdf(linspace(min(abs(Yerror))...
        ,max(abs(Yerror))),mean(abs(Yerror)),std(abs(Yerror))),"-",'linewidth', 1.5);
    hold on;
end
figure(1);
subplot(2,3,1);
grid on;
lgd = legend((filenames),"location","Southeast","Linewidth",1.5);
lgd.FontSize = 12;
ttl = title("Empherical CDF of X-axis error");
ttl.FontSize = 14;
xlabel("Error of X-axis (m)");
ylabel("Probability");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;

subplot(2,3,2);
grid on;
lgd = legend((filenames),"location","Southeast","Linewidth",1.5);
lgd.FontSize = 12;
ttl = title("Theoretical CDF of X-axis error");
ttl.FontSize = 14;
xlabel("Error of X-axis (m)");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;

subplot(2,3,3);
grid on;
lgd = legend((filenames),"location","Southeast","Linewidth",1.5);
lgd.FontSize = 12;
ttl = title("Theoretical CDF of X-axis absolute error");
ttl.FontSize = 14;
xlabel("Absolute error of X-axis (m)");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;

subplot(2,3,4);
grid on;
lgd = legend((filenames),"location","Southeast","Linewidth",1.5);
lgd.FontSize = 12;
ttl = title("Empherical CDF of Y-axis error");
ttl.FontSize = 14;
xlabel("Error of Y-axis (m)");
ylabel("Probability");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;

subplot(2,3,5);
grid on;
lgd = legend((filenames),"location","Southeast","Linewidth",1.5);
lgd.FontSize = 12;
ttl = title("Theoretical CDF of Y-axis error");
ttl.FontSize = 14;
xlabel("Error of Y-axis (m)");
axs = gca;
axs.XAxis.FontSize = 12;
axs.YAxis.FontSize = 12;
hold off;

subplot(2,3,6);
grid on;
lgd = legend((filenames),"location","Southeast","Linewidth",1.5);
lgd.FontSize = 12;
ttl = title("Theoretical CDF of Y-axis absolute error");
ttl.FontSize = 14;
xlabel("Aboslute error of Y-axis (m)");
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