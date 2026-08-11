function suite = run_publication_demo_suite(projectRoot, outputRoot, seed, verifyDeterminism)
%RUN_PUBLICATION_DEMO_SUITE Backward-compatible entry for the single-figure suite.
if nargin < 1 || isempty(projectRoot)
    projectRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
end
if nargin < 2 || isempty(outputRoot)
    outputRoot = fullfile(projectRoot, 'output', '_demos', 'matlab', 'matlab-single-figure-suite');
end
if nargin < 3 || isempty(seed), seed = 20260801; end
if nargin < 4, verifyDeterminism = false; end
suite = run_single_figure_suite(projectRoot, outputRoot, seed, verifyDeterminism);
end
