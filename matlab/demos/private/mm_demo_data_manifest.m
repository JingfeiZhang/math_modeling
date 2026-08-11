function manifest = mm_demo_data_manifest(folder, relativeFiles)
%MM_DEMO_DATA_MANIFEST Hash deterministic source files for a demo fixture.
folder = char(folder);
relativeFiles = cellstr(relativeFiles);
rows = repmat(struct('path', '', 'bytes', 0, 'sha256', ''), numel(relativeFiles), 1);
for index = 1:numel(relativeFiles)
    relative = relativeFiles{index};
    path = fullfile(folder, relative);
    assert(isfile(path), 'Missing demo source data: %s', path);
    info = dir(path);
    rows(index).path = strrep(relative, '\\', '/');
    rows(index).bytes = info.bytes;
    rows(index).sha256 = mm_demo_sha256(path);
end
manifest = struct('schema_version', 1, 'files', rows, ...
    'determinism_note', 'CSV and JSON hashes are deterministic; MAT raw hashes are provenance only.');
end
