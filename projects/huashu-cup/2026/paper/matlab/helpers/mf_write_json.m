function mf_write_json(path, value)
% Write indented UTF-8 JSON.
folder = fileparts(path);
if ~isfolder(folder)
    mkdir(folder);
end
fid = fopen(path, 'w', 'n', 'UTF-8');
if fid < 0
    error('matlabFigures:JsonOpenFailed', 'Cannot write JSON: %s', path);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '%s\n', jsonencode(value, 'PrettyPrint', true));
clear cleanup;
end
