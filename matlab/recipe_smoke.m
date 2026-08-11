function recipe_smoke(outputRoot)
% Run publication recipes against fixed test evidence only.
arguments
    outputRoot (1,1) string
end
workspaceRoot = string(fileparts(fileparts(mfilename('fullpath'))));
hashRoot = fullfile(workspaceRoot, 'matlab');
recipeRoot = fullfile(workspaceRoot, 'templates', 'figures', 'matlab');
fixtureRoot = fullfile(workspaceRoot, 'tests', 'fixtures', 'matlab');
addpath(hashRoot);
addpath(recipeRoot);
cleanup = onCleanup(@() removeRecipePaths(recipeRoot, hashRoot));

plot_sensitivity_curve( ...
    fullfile(fixtureRoot, 'sensitivity.csv'), outputRoot, ...
    "sensitivity", "Demand factor", "dimensionless", "Profit", "CNY");
plot_optimization_convergence( ...
    fullfile(fixtureRoot, 'convergence.csv'), outputRoot, ...
    "convergence", "Objective", "CNY");
hashFigureArtifacts(outputRoot, "sensitivity");
hashFigureArtifacts(outputRoot, "convergence");

required = [
    "sensitivity.pdf", "sensitivity.svg", "sensitivity.png", ...
    "convergence.pdf", "convergence.svg", "convergence.png", ...
    "sensitivity.hashes.json", "convergence.hashes.json"
];
for name = required
    target = fullfile(outputRoot, name);
    if ~isfile(target)
        error('mathmodeling:MissingRecipeOutput', 'Missing recipe output: %s', target);
    end
end
end

function removeRecipePaths(recipeRoot, hashRoot)
rmpath(recipeRoot);
rmpath(hashRoot);
end
