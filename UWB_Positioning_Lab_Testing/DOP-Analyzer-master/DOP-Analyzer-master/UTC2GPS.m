function [wn, tow] = UTC2GPS(date)
date = fix(date);
t0 = [1980 1 6 00 00 00];
[leapsecs, n] = leapseconds();
diff = etime(date, t0);
for i = 1:n
    if etime(date, leapsecs(i, :)) > 1
        diff = diff + 1;
    end
end
wn = floor(diff/604800);
tow = diff - wn*604800;