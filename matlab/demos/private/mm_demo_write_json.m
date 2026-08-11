function mm_demo_write_json(path, value)
%MM_DEMO_WRITE_JSON Write a UTF-8, human-readable JSON artifact.
path = char(path);
parent = fileparts(path);
if ~isempty(parent) && ~isfolder(parent)
    mkdir(parent);
end
fileId = fopen(path, 'w', 'n', 'UTF-8');
assert(fileId >= 0, 'Unable to write JSON artifact: %s', path);
cleanup = onCleanup(@() fclose(fileId)); %#ok<NASGU>
fwrite(fileId, jsonencode(value, PrettyPrint=true), 'char');
end
