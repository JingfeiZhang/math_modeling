projectRoot = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot, 'matlab'));
workspace = setup_modeling_path(projectRoot);

report = struct();
report.generatedAt = char(datetime('now', 'TimeZone', 'Asia/Shanghai', ...
    'Format', 'yyyy-MM-dd''T''HH:mm:ssXXX'));
report.matlab = struct('version', version, 'release', version('-release'), ...
    'architecture', computer('arch'), 'root', matlabroot);
report.capabilities = struct();

functionNames = {'tiledlayout', 'exportgraphics', 'optimproblem', 'ga', 'sym', ...
    'fitlm', 'fitctree', 'boxchart'};
for index = 1:numel(functionNames)
    functionName = functionNames{index};
    report.capabilities.(functionName) = ~isempty(which(functionName));
end

report.products = struct( ...
    'optimization', ~isempty(ver('optim')), ...
    'globalOptimization', ~isempty(ver('globaloptim')), ...
    'symbolicMath', ~isempty(ver('symbolic')), ...
    'statisticsMachineLearning', ~isempty(ver('stats')), ...
    'parallelComputing', ~isempty(ver('parallel')), ...
    'mapping', ~isempty(ver('map')));

checks = struct();
try
    testFig = figure('Visible', 'off');
    testLayout = tiledlayout(testFig, 1, 1);
    testAxes = nexttile(testLayout);
    plot(testAxes, 0:2, [0, 1, 0]);
    graphicsPath = fullfile(workspace.outputRoot, 'smoke_graphics.png');
    exportgraphics(testFig, graphicsPath, 'Resolution', 150);
    checks.graphics = isfile(graphicsPath) && dir(graphicsPath).bytes > 0;
    close(testFig);
catch exception
    if exist('testFig', 'var') && isgraphics(testFig)
        close(testFig);
    end
    checks.graphics = false;
    checks.graphicsError = exception.message;
end

try
    options = optimoptions('quadprog', 'Display', 'none');
    [solution, objective, exitflag] = quadprog(2, -4, [], [], [], [], 0, [], [], options);
    checks.optimization = exitflag > 0 && abs(solution - 2) < 1e-6 && abs(objective + 4) < 1e-8;
catch exception
    checks.optimization = false;
    checks.optimizationError = exception.message;
end

try
    gaOptions = optimoptions('ga', 'Display', 'none', 'PopulationSize', 10, ...
        'MaxGenerations', 2, 'UseParallel', false);
    [~, gaValue] = ga(@(value) (value - 1.5).^2, 1, [], [], [], [], -5, 5, [], gaOptions);
    checks.globalOptimization = isfinite(gaValue);
catch exception
    checks.globalOptimization = false;
    checks.globalOptimizationError = exception.message;
end

try
    symbolicX = sym('x');
    checks.symbolicMath = isequal(diff(symbolicX^3, symbolicX), 3 * symbolicX^2);
catch exception
    checks.symbolicMath = false;
    checks.symbolicMathError = exception.message;
end

try
    predictor = (1:20).';
    response = 2 + 3 * predictor + 0.1 * sin(predictor);
    linearModel = fitlm(predictor, response);

    classPredictor = (0:11).';
    classResponse = categorical([zeros(6, 1); ones(6, 1)]);
    treeModel = fitctree(classPredictor, classResponse, ...
        'MinLeafSize', 1, 'MaxNumSplits', 3, 'Prune', 'off');
    predictedClass = predict(treeModel, [1; 10]);

    checks.statisticsMachineLearning = ...
        abs(linearModel.Coefficients.Estimate(2) - 3) < 0.02 && ...
        string(predictedClass(1)) == "0" && string(predictedClass(2)) == "1";
    checks.statisticsSlope = linearModel.Coefficients.Estimate(2);
catch exception
    checks.statisticsMachineLearning = false;
    checks.statisticsMachineLearningError = exception.message;
end

report.checks = checks;
report.requiredChecksPassed = checks.graphics && checks.optimization && ...
    checks.globalOptimization && checks.symbolicMath && checks.statisticsMachineLearning;
report.optionalStatisticsAvailable = report.products.statisticsMachineLearning && ...
    report.capabilities.fitlm && report.capabilities.fitctree && ...
    report.capabilities.boxchart && checks.statisticsMachineLearning;

reportPath = fullfile(projectRoot, 'output', 'matlab_environment.json');
fileId = fopen(reportPath, 'w', 'n', 'UTF-8');
assert(fileId >= 0, 'Unable to open MATLAB environment report.');
fwrite(fileId, jsonencode(report, PrettyPrint=true), 'char');
fclose(fileId);

fprintf('MATLAB %s (%s) smoke test: required=%d, statistics=%d\n', ...
    report.matlab.release, report.matlab.architecture, ...
    report.requiredChecksPassed, report.optionalStatisticsAvailable);
assert(report.requiredChecksPassed, 'One or more required MATLAB smoke checks failed.');
