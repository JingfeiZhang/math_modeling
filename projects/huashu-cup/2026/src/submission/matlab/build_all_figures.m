function buildReport = build_all_figures(projectRoot, stagingRoot)
% Build all twelve formal paper figures and record output hashes.
scriptDir = fileparts(mfilename('fullpath'));
if nargin < 1 || strlength(string(projectRoot)) == 0
    projectRoot = fileparts(fileparts(scriptDir));
end
if nargin < 2 || strlength(string(stagingRoot)) == 0
    stagingRoot = scriptDir;
end
projectRoot = string(projectRoot);
stagingRoot = string(stagingRoot);
addpath(fullfile(stagingRoot, 'helpers'));
addpath(fullfile(stagingRoot, 'figures'));
outputDir = fullfile(fileparts(stagingRoot), 'figures');
reportDir = fullfile(stagingRoot, 'reports');
if ~isfolder(outputDir), mkdir(outputDir); end
if ~isfolder(reportDir), mkdir(reportDir); end

inputReport = prepare_figure_data(projectRoot, stagingRoot);
loaded = load(fullfile(stagingRoot, 'derived', 'figure_data.mat'), 'D');
D = loaded.D;
S = mf_style();

builders = { ...
    @() fig_q1_weekly_demand_structure(D.q1Weekly, outputDir, S), ...
    @() fig_q1_blind_forecast_interval(D.q1Forecast, outputDir, S), ...
    @() fig_q1_series_error_pairing(D.q1ErrorPairs, outputDir, S), ...
    @() fig_q1_schedule_gantt(D.q1Schedule, outputDir, S), ...
    @() fig_q1_resource_headroom(D.q1Headroom, outputDir, S), ...
    @() fig_q2_load_migration(D.q2Migration, outputDir, S), ...
    @() fig_q2_cumulative_impact(D.q2Cumulative, outputDir, S), ...
    @() fig_q2_latency_ecdf(D.q2Latency, outputDir, S), ...
    @() fig_q3_dispatch_soc(D.q3Dispatch, outputDir, S), ...
    @() fig_q3_rolling_runtime_coverage(D.q3Runtime, outputDir, S), ...
    @() fig_q4_scenario_tradeoff(D.q4Tradeoff, outputDir, S), ...
    @() fig_q4_system_profile(D.q4Profile, outputDir, S) ...
    };
stems = [ ...
    "fig-q1-weekly-demand-structure"; "fig-q1-blind-forecast-interval"; ...
    "fig-q1-series-error-pairing"; "fig-q1-schedule-gantt"; ...
    "fig-q1-resource-headroom"; "fig-q2-load-migration"; ...
    "fig-q2-cumulative-impact"; "fig-q2-latency-ecdf"; ...
    "fig-q3-dispatch-soc"; "fig-q3-rolling-runtime-coverage"; ...
    "fig-q4-scenario-tradeoff"; "fig-q4-system-profile" ...
    ];

records = repmat(struct('stem', "", 'status', "", 'duration_s', 0, ...
    'outputs', [], 'error', ""), numel(builders), 1);
failed = false;
for k = 1:numel(builders)
    records(k).stem = stems(k);
    started = tic;
    try
        outputs = builders{k}();
        hashes = repmat(struct('path', "", 'sha256', "", 'bytes', 0), numel(outputs), 1);
        for j = 1:numel(outputs)
            info = dir(outputs(j));
            [~, ~, extension] = fileparts(outputs(j));
            hashes(j).path = string(fullfile('outputs', stems(k) + string(extension)));
            hashes(j).sha256 = mf_sha256(outputs(j));
            hashes(j).bytes = info.bytes;
        end
        records(k).status = "PASS";
        records(k).outputs = hashes;
    catch ME
        failed = true;
        records(k).status = "FAIL";
        records(k).error = string(getReport(ME, 'extended', 'hyperlinks', 'off'));
    end
    records(k).duration_s = toc(started);
end

buildReport = struct();
buildReport.schema_version = 1;
buildReport.project_id = "huashu-cup-2026";
buildReport.problem_id = "C";
buildReport.backend = "MATLAB";
buildReport.matlab_version = string(version);
buildReport.matlab_release = string(version('-release'));
buildReport.platform = string(computer);
buildReport.generated_at = string(datetime('now', 'TimeZone', 'local', ...
    'Format', 'yyyy-MM-dd''T''HH:mm:ssXXX'));
buildReport.palette_id = S.paletteId;
buildReport.figure_width_mm = S.widthCm * 10;
buildReport.minimum_font_pt = S.minFontSize;
buildReport.png_dpi = S.pngDpi;
buildReport.input_manifest_sha256 = inputReport.derived_data.sha256;
sourceListing = [dir(fullfile(stagingRoot, '*.m')); ...
    dir(fullfile(stagingRoot, 'helpers', '*.m')); ...
    dir(fullfile(stagingRoot, 'figures', '*.m'))];
sourceHashes = repmat(struct('path', "", 'sha256', "", 'bytes', 0), numel(sourceListing), 1);
for k = 1:numel(sourceListing)
    sourcePath = string(fullfile(sourceListing(k).folder, sourceListing(k).name));
    sourceHashes(k).path = erase(sourcePath, stagingRoot + filesep);
    sourceHashes(k).sha256 = mf_sha256(sourcePath);
    sourceHashes(k).bytes = sourceListing(k).bytes;
end
buildReport.source_hashes = sourceHashes;
buildReport.figures = records;
buildReport.all_passed = ~failed;
mf_write_json(fullfile(reportDir, 'build_report.json'), buildReport);
if failed
    error('matlabFigures:BuildFailed', 'One or more staging figures failed. See reports/build_report.json.');
end
end
