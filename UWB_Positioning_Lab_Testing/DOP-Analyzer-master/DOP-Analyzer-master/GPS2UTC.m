function utctime = GPS2UTC(wn, tow)
t = datenum(1980, 1, 6, 0, 0, 0);
t = t + wn*7 + tow/(60*60*24);
[leapsecs, n] = leapseconds();
for i = 1:n
    if etime(datevec(t), leapsecs(i, :)) > 1
        t = t - 1/(60*60*24);
    end
end
utctime = fix(datevec(t));