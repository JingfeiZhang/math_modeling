function info = setup_modeling_path(projectRoot)
%SETUP_MODELING_PATH Add competition MATLAB code and prepare output paths.

if nargin < 1 || strlength(string(projectRoot)) == 0
    projectRoot = fileparts(fileparts(mfilename('fullpath')));
end
projectRoot = char(java.io.File(projectRoot).getCanonicalPath());
matlabRoot = fullfile(projectRoot, 'matlab');
sourceRoot = fullfile(projectRoot, 'src');
outputRoot = fullfile(projectRoot, 'output', '_demos', 'matlab', 'matlab_figures');

addpath(genpath(matlabRoot));
if isfolder(sourceRoot)
    addpath(genpath(sourceRoot));
end
if ~isfolder(outputRoot)
    mkdir(outputRoot);
end

info = struct( ...
    'projectRoot', projectRoot, ...
    'matlabRoot', matlabRoot, ...
    'outputRoot', outputRoot, ...
    'release', version('-release'), ...
    'version', version, ...
    'architecture', computer('arch'));
end
