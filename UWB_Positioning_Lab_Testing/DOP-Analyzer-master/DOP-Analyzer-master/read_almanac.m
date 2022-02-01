% Parses an SEM almanac file. File format specification can be fount at
% http://www.navcen.uscg.gov/?pageName=gpsSem
% Takes a filename as input.
function almanac = read_almanac(filename)
    % Open files
    file_id = fopen(filename, 'r');
    
    % First line contains the number of records and a title...
    input = textscan(file_id, '%d %s', 1, 'delimiter', '\n');
    n_records = input{1};
    title = input{2};
    
    % Week number and TOA
    input = textscan(file_id, '%d %d', 1, 'delimiter', '\n');
    wn = double(input{1});
    wn_nov = 1024+wn;   % Add a field assuming week number overflowed 1 time...
    toa = double(input{2});
    
    % Initialize entries array
    entries = [];
    
    % Parse entries...
    for n = 1:n_records
    
        % Empty line...
        textscan(file_id, '%s', 1, 'delimiter', '\n');
        
        % PRN
        input = textscan(file_id, '%d', 1, 'delimiter', '\n');
        prn = input{1};
        
        % SVN
        input = textscan(file_id, '%d', 1, 'delimiter', '\n');
        svn = input{1};
        
        % Average URA
        input = textscan(file_id, '%d', 1, 'delimiter', '\n');
        ura = input{1};
        
        % Eccentricity, inclination offset and rate of right ascension
        input = textscan(file_id, '%f %f %f', 1, 'delimiter', '\n');
        e = input{1};
        di = input{2}*pi;
        omegadot = input{3}*pi;
        
        % Square root of semi-major axis, longitude of orbital plane and
        % argument of perigee
        input = textscan(file_id, '%f %f %f', 1, 'delimiter', '\n');
        sqrt_a = input{1};
        omega0 = input{2}*pi;
        w = input{3}*pi;
    
        % Mean anomaly, zeroth order clock correction and first order clock correction
        input = textscan(file_id, '%f %f %f', 1, 'delimiter', '\n');
        m0 = input{1}*pi;
        af0 = input{2};
        af1 = input{3};
    
        % Satellite health
        input = textscan(file_id, '%d', 1, 'delimiter', '\n');
        health = input{1};
    
        % Satellite configuration
        input = textscan(file_id, '%d', 1, 'delimiter', '\n');
        conf = input{1};
    
        % Create entry struct and append it to the array...
        sat = struct('prn', prn, 'svn', svn, 'ura', ura, 'e', e, 'di', di, 'omegadot', omegadot, 'sqrt_a', sqrt_a, 'omega0', omega0, 'w', w, 'm0', m0, 'af0', af0, 'af1', af1, 'health', health, 'conf', conf);
        entries = [entries; sat];
    end
    
    % Final struct
    almanac = struct('title', title, 'wn', wn, 'wn_nov', wn_nov, 'toa', toa, 'entries', entries);
end