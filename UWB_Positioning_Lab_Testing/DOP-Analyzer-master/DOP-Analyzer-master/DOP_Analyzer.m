function varargout = DOP_Analyzer(varargin)
% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @DOP_Analyzer_OpeningFcn, ...
                   'gui_OutputFcn',  @DOP_Analyzer_OutputFcn, ...
                   'gui_LayoutFcn',  [] , ...
                   'gui_Callback',   []);
if nargin && ischar(varargin{1})
    gui_State.gui_Callback = str2func(varargin{1});
end

if nargout
    [varargout{1:nargout}] = gui_mainfcn(gui_State, varargin{:});
else
    gui_mainfcn(gui_State, varargin{:});
end
% End initialization code - DO NOT EDIT
format long

function DOP_Analyzer_OpeningFcn(hObject, eventdata, handles, varargin)
handles.output = hObject;
guidata(hObject, handles);

function varargout = DOP_Analyzer_OutputFcn(hObject, eventdata, handles) 
varargout{1} = handles.output;

function almanac_path_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function almanac_wov_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function almanac_day_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function almanac_hour_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function almanac_month_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function almanac_year_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function almanac_mins_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function almanac_secs_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function ephemeris_toe_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function ephemeris_wn_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function grid_lat_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function grid_long_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function dop_min_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function dop_max_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function dop_mean_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function point_data_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function text400_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function text401_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function point_lat_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function point_long_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function toe_day_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function toe_hour_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function toe_month_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function toe_year_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function toe_mins_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function toe_secs_CreateFcn(hObject, eventdata, handles)
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

function almanac_download_Callback(hObject, eventdata, handles)
[file, path] = uiputfile('*.al3', 'Where to save?');
if not(isequal(file, 0))
    filepath = strcat(path, file);
    url = 'http://www.navcen.uscg.gov/?pageName=currentAlmanac&format=sem';
    urlwrite(url, filepath);
    almanac = read_almanac(filepath);
    wov = str2num(get(handles.almanac_wov, 'String'));
    if isempty(wov)
        errordlg('Wrong week overflow...');
        return;
    end
    almanac.wn_nov = wov*1024+almanac.wn;
    utctime = GPS2UTC(almanac.wn_nov, almanac.toa);
    set(handles.almanac_path, 'String', filepath);
    set(handles.almanac_year, 'String', utctime(1));
    set(handles.almanac_month, 'String', utctime(2));
    set(handles.almanac_day, 'String', utctime(3));
    set(handles.almanac_hour, 'String', utctime(4));
    set(handles.almanac_mins, 'String', utctime(5));
    set(handles.almanac_secs, 'String', utctime(6));
    set(handles.toe_year, 'String', utctime(1));
    set(handles.toe_month, 'String', utctime(2));
    set(handles.toe_day, 'String', utctime(3));
    set(handles.toe_hour, 'String', utctime(4));
    set(handles.toe_mins, 'String', utctime(5));
    set(handles.toe_secs, 'String', utctime(6));
    handles.almanac=almanac;
    guidata(hObject, handles)
end

function almanac_select_Callback(hObject, eventdata, handles)
[file, path] = uigetfile('*.al3', 'Select an almanac file...');
if not(isequal(file, 0))
    fullpath = strcat(path, file);
    almanac = read_almanac(fullpath);
    wov = str2num(get(handles.almanac_wov, 'String'));
    if isempty(wov)
        errordlg('Wrong week overflow...');
        return;
    end
    almanac.wn_nov = wov*1024+almanac.wn;
    utctime = GPS2UTC(almanac.wn_nov, almanac.toa);
    set(handles.almanac_path, 'String', fullpath);
    set(handles.almanac_year, 'String', utctime(1));
    set(handles.almanac_month, 'String', utctime(2));
    set(handles.almanac_day, 'String', utctime(3));
    set(handles.almanac_hour, 'String', utctime(4));
    set(handles.almanac_mins, 'String', utctime(5));
    set(handles.almanac_secs, 'String', utctime(6));
    set(handles.toe_year, 'String', utctime(1));
    set(handles.toe_month, 'String', utctime(2));
    set(handles.toe_day, 'String', utctime(3));
    set(handles.toe_hour, 'String', utctime(4));
    set(handles.toe_mins, 'String', utctime(5));
    set(handles.toe_secs, 'String', utctime(6));
    handles.almanac=almanac;
    guidata(hObject, handles)
end

function almanac_wov_Callback(hObject, eventdata, handles)
    if not(isfield(handles, 'almanac'))
        return;
    end
    wov = str2num(get(handles.almanac_wov, 'String'));
    if isempty(wov)
        errordlg('Wrong week overflow...');
        return;
    end
    handles.almanac.wn_nov = wov*1024+handles.almanac.wn;
    utctime = GPS2UTC(handles.almanac.wn_nov, handles.almanac.toa);
    set(handles.almanac_year, 'String', utctime(1));
    set(handles.almanac_month, 'String', utctime(2));
    set(handles.almanac_day, 'String', utctime(3));
    set(handles.almanac_hour, 'String', utctime(4));
    set(handles.almanac_mins, 'String', utctime(5));
    set(handles.almanac_secs, 'String', utctime(6));
    set(handles.toe_year, 'String', utctime(1));
    set(handles.toe_month, 'String', utctime(2));
    set(handles.toe_day, 'String', utctime(3));
    set(handles.toe_hour, 'String', utctime(4));
    set(handles.toe_mins, 'String', utctime(5));
    set(handles.toe_secs, 'String', utctime(6));
    handles.almanac=almanac;
    guidata(hObject, handles)

function paint_sphere(base, handle, satellites, show_sats)
axes(handle);
reset(handle);
cla;
colormap jet;
load coast;
axesm('globe', 'Grid', 'on');
plotm(lat, long, 'Color', 'k');
view(3);
axis vis3d;
axis off;
rotate3d on;
zoom(1);
baseR = makerefmat('RasterSize', size(base), 'Latlim', [-90 90], 'Lonlim', [0 360]);
meshm(base, baseR, size(base));
colorbar;
caxis([min(min(base)), max(max(base))])
if not(isempty(satellites)) && show_sats == 1
    [x y z] = sphere();
    scale = 0.05;
    for i = 1:size(satellites(:,1))
        p = satellites(i, :)/10000000;
        surf(scale*x+p(1), scale*y+p(2), scale*z+p(3));
    end
end

function paint_plane(base, handle, satellites, show_sats)
axes(handle);
reset(handle);
cla;
colormap jet;
axis off;
axesm('globe', 'Grid', 'on');
worldmap('World');
setm(gca,'Origin', [0 180]);
rotate3d off;
view(2);
zoom(0.8);
baseR = makerefmat('RasterSize', size(base), 'Latlim', [-90 90], 'Lonlim', [0 360]);
meshm(base, baseR, size(base));
colorbar;
load coast;
geoshow(lat, long, 'Color', 'k');
if not(isempty(satellites)) && show_sats == 1
    for i = 1:size(satellites(:,1))
        p = satellites(i, :);
        [lat lon h] = ecef2geodetic(p(1), p(2), p(3), referenceEllipsoid('wgs84'));
        geoshow(lat*180/pi, lon*180/pi, 'DisplayType', 'Point', 'Color', 'k');
    end
end

function calculate_Callback(hObject, eventdata, handles)
if not(isfield(handles, 'almanac'))
    errordlg('Please select an almanac...');
    return;
end
ephemeris_year = str2num(get(handles.toe_year, 'String'));
if isempty(ephemeris_year)
    errordlg('Wrong ephemeris year number...');
    return;
end
ephemeris_month = str2num(get(handles.toe_month, 'String'));
if isempty(ephemeris_month)
    errordlg('Wrong ephemeris month number...');
    return;
end
ephemeris_day = str2num(get(handles.toe_day, 'String'));
if isempty(ephemeris_day)
    errordlg('Wrong ephemeris day number...');
    return;
end
ephemeris_hour = str2num(get(handles.toe_hour, 'String'));
if isempty(ephemeris_hour)
    errordlg('Wrong ephemeris hour number...');
    return;
end
ephemeris_mins = str2num(get(handles.toe_mins, 'String'));
if isempty(ephemeris_mins)
    errordlg('Wrong ephemeris mins number...');
    return;
end
ephemeris_secs = str2num(get(handles.toe_secs, 'String'));
if isempty(ephemeris_secs)
    errordlg('Wrong ephemeris secs number...');
    return;
end
[ephemeris_wn, ephemeris_toe] = UTC2GPS([ephemeris_year, ephemeris_month, ephemeris_day, ephemeris_hour, ephemeris_mins, ephemeris_secs]);
grid_long = str2num(get(handles.grid_long, 'String'));
if isempty(grid_long)
    errordlg('Wrong longitude points...');
    return;
end
grid_lat = str2num(get(handles.grid_lat, 'String'));
if isempty(grid_lat)
    errordlg('Wrong latitude points...');
    return;
end
calc = -1;
if get(handles.calc_hdop, 'Value') == get(handles.calc_hdop, 'Max')
    calc = 1;
elseif get(handles.calc_vdop, 'Value') == get(handles.calc_vdop, 'Max')
    calc = 2;
elseif get(handles.calc_tdop, 'Value') == get(handles.calc_tdop, 'Max')
    calc = 3;
else
    errordlg('Wrong calculus variable...');
    return;
end
% Calculate the position of every satellite in ECEF...
diag = waitbar(0, 'Calculating...', 'CreateCancelBtn', 'setappdata(gcbf,''canceling'',1)');
setappdata(diag, 'canceling', 0)
satellites = ephemeris(handles.almanac, ephemeris_wn, ephemeris_toe);
userecef = zeros(1, 3);
base = zeros(grid_lat, grid_long);
for i = 0:grid_lat-1
    for j = 0:grid_long-1
        % Handle the cancel signal...
        if getappdata(diag, 'canceling')
            delete(diag);
            return
        end
        % Calculate user position...
        [x y z] = geodetic2ecef(-pi/2+i*pi/grid_lat, j*2*pi/grid_long, 0, referenceEllipsoid('wgs84'));
        userecef = [x y z];
        userecefu = userecef/norm(userecef);
        % For the user position calculate which satellites are visible and
        % build the H matrix for DOP calculus...
        H = [];
        for k = 1:size(handles.almanac.entries)
            rus = satellites(k, :)-userecef;
            rusu = rus/norm(rus);
            if abs(acos(dot(userecefu, rusu))) < pi/2
                % Satelite is visible
                [sEast, sNorth, sUp] = ecef2enu(satellites(k, 1), satellites(k, 2), satellites(k, 3), -pi/2+i*pi/grid_lat, j*2*pi/grid_long, 0, referenceEllipsoid('wgs84'), 'radians');
                enucoords=[double(sEast), double(sNorth), double(sUp)];
                enucoords=-enucoords/norm(enucoords);                
                H = [H; enucoords 1];
            end
        end
        if isempty(H)
            base(i+1,j+1) = inf;
            disp('Coordinates without coverage!');
        else
            G = inv(H'*H);
            switch calc
                case 1
                    base(i+1,j+1) = sqrt(G(1,1)+G(2,2));
                case 2
                    base(i+1,j+1) = sqrt(G(3,3));
                case 3
                    base(i+1,j+1) = sqrt(G(1,1)+G(2,2)+G(3,3));
            end
        end
        waitbar((i*grid_long+j)/(grid_lat*grid_long), diag);
    end
end
delete(diag);
set(handles.dop_min, 'String', min(min(base)));
set(handles.dop_max, 'String', max(max(base)));
set(handles.dop_mean, 'String', mean(mean(base)));
handles.satellites=satellites;
handles.base=base;
guidata(hObject, handles)
view_graph_Callback(hObject, eventdata, handles)
point_query_Callback(hObject, eventdata, handles)

function point_query_Callback(hObject, eventdata, handles)
if not(isfield(handles, 'base'))
    errordlg('Please calculate first...');
    return;
end
point_lat = str2double(get(handles.point_lat, 'String'));
if isempty(point_lat)
    errordlg('Wrong latitude point...');
    return;
end
point_long = str2double(get(handles.point_long, 'String'));
if isempty(point_long)
    errordlg('Wrong latitude point...');
    return;
end
if point_long < 0
    point_long = point_long + 360;
end
[grid_lat, grid_long] = size(handles.base);
base_lat = round((point_lat+90)*grid_lat/180);
if base_lat == 0
    base_lat = 1;
end
base_long = round(point_long*grid_long/360);
if base_long == 0
    base_long = 1;
end
data=handles.base(base_lat, base_long);
set(handles.point_data, 'String', data);

function view_graph_Callback(hObject, eventdata, handles)
if not(isfield(handles, 'base'))
    errordlg('Please calculate first...');
    return;
end
show_sats = (get(handles.show_sats, 'Value') == get(handles.show_sats, 'Max'));
if get(handles.view_3d, 'Value') == get(handles.view_3d, 'Max')
    paint_sphere(handles.base, handles.world, handles.satellites, show_sats);
elseif get(handles.view_2d, 'Value') == get(handles.view_2d, 'Max')
    paint_plane(handles.base, handles.world, handles.satellites, show_sats);
else
    errordlg('Please select a view...');
    return;
end
