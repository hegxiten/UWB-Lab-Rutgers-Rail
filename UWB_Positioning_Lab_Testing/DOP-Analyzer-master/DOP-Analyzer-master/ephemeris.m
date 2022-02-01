function satellites = ephemeris(almanac, wn, toe)
mu = 3.986005e14;
i0 = 0.3*pi;
omegae = 7.2921151467e-5;
tk = (wn-almanac.wn_nov)*604800+(toe-almanac.toa);
if wn-almanac.wn_nov > 0
    warndlg('Ephemeris time is too far away from time of applicability...');
end
entries = size(almanac.entries);
satellites = zeros(entries(1), 3);
options = optimset('Display', 'off');
for i = 1:size(almanac.entries)
    a = almanac.entries(i).sqrt_a^2;
    n0 = sqrt(mu/(a^3));
    mk = almanac.entries(i).m0 + n0*tk;
    Ek = fsolve(@(x) x-almanac.entries(i).e*x-double(mk), 0, options);
    vk = atan2(sqrt(1-almanac.entries(i).e^2)*sin(Ek)/(1-almanac.entries(i).e*cos(Ek)), (cos(Ek)-almanac.entries(i).e)/(1-almanac.entries(i).e*cos(Ek)));
    % Ek = acos((almanac.entries(i).e+cos(vk))/(1+almanac.entries(i).e*cos(vk)));
    % Same as previous Ek
    uk = vk + almanac.entries(i).w;
    rk = a*(1-almanac.entries(i).e*cos(Ek));
    ik = i0 + almanac.entries(i).di;
    xk0 = rk*cos(uk);
    yk0 = rk*sin(uk);
    % Check why we have to convert from int32 to double...
    omegak = almanac.entries(i).omega0+(almanac.entries(i).omegadot-omegae)*tk-omegae*toe;
    xk = xk0*cos(omegak)-yk0*cos(ik)*sin(omegak);
    yk = xk0*sin(omegak)+yk0*cos(ik)*cos(omegak);
    zk = yk0*sin(ik);
    % Add satellite to list...
    satellites(i, :) = [xk yk zk];
end
end
