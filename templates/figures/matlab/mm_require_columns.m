function mm_require_columns(T, required)
% Fail closed when an evidence table does not expose the declared contract.
names = string(T.Properties.VariableNames);
missing = setdiff(string(required), names, 'stable');
if ~isempty(missing)
    error('mathmodeling:MissingColumns', 'Evidence table is missing columns: %s', strjoin(missing, ', '));
end
if height(T) == 0
    error('mathmodeling:EmptyEvidence', 'Evidence table is empty.');
end
end
