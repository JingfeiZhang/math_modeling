function mf_require_columns(T, required, sourceName)
% Fail closed when a frozen source does not expose the declared fields.
if nargin < 3
    sourceName = "evidence table";
end
missing = setdiff(string(required), string(T.Properties.VariableNames), 'stable');
if ~isempty(missing)
    error('matlabFigures:MissingColumns', '%s is missing columns: %s', ...
        sourceName, strjoin(missing, ', '));
end
if height(T) == 0
    error('matlabFigures:EmptyEvidence', '%s is empty.', sourceName);
end
end
