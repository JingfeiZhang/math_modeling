function values = mm_num(T, name)
% Convert a declared numeric evidence column without inventing defaults.
raw = T.(name);
values = str2double(string(raw));
if any(~isfinite(values))
    error('mathmodeling:NonNumericEvidence', 'Column %s contains non-finite values.', name);
end
values = values(:);
end
