function outputs = fig_q2_latency_ecdf(D, outputDir, S)
% Compare paired latency summaries when the raw ECDF is dominated by one value.
fig = mf_publication_figure(S);
ax = axes(fig, 'Position', [0.15, 0.16, 0.80, 0.66]);

baseRaw = double(D.baselineMs(:));
candRaw = double(D.candidateMs(:));
if numel(baseRaw) ~= numel(candRaw) || isempty(baseRaw) || ...
        any(~isfinite(baseRaw)) || any(~isfinite(candRaw))
    error('matlabFigures:Q2LatencyData', ...
        'Q2 latency vectors must be finite, nonempty, and equally sized.');
end
if isfield(D, 'baselineTaskCount') && numel(baseRaw) ~= D.baselineTaskCount
    error('matlabFigures:Q2LatencyCount', ...
        'Q2 baseline task count is inconsistent with the plotted data.');
end
if isfield(D, 'candidateTaskCount') && numel(candRaw) ~= D.candidateTaskCount
    error('matlabFigures:Q2LatencyCount', ...
        'Q2 candidate task count is inconsistent with the plotted data.');
end
if isfield(D, 'baselineSlaViolationRate') && D.baselineSlaViolationRate ~= 0
    error('matlabFigures:Q2LatencySLA', 'Q2 baseline SLA audit is not zero.');
end
if isfield(D, 'candidateSlaViolationRate') && D.candidateSlaViolationRate ~= 0
    error('matlabFigures:Q2LatencySLA', 'Q2 candidate SLA audit is not zero.');
end

% Type-7 empirical percentiles match MATLAB's linear interpolation convention.
probabilities = [0.50, 0.90, 0.95, 0.99];
baseStats = [mean(baseRaw); linear_percentile(baseRaw, probabilities); max(baseRaw)];
candStats = [mean(candRaw); linear_percentile(candRaw, probabilities); max(candRaw)];
deltaStats = candStats - baseStats;
statLabels = {'Mean'; 'P50'; 'P90'; 'P95'; 'P99'; 'Max'};
y = (1:numel(statLabels)).';
yBase = y - 0.075;
yCand = y + 0.075;
xMax = max(100, 10 * ceil((max([baseStats; candStats]) + 14) / 10));
xOffset = 0.018 * xMax;

hold(ax, 'on');
for k = 2:2:numel(y)
    patch(ax, [0, xMax, xMax, 0], ...
        [k - 0.45, k - 0.45, k + 0.45, k + 0.45], ...
        S.colors.fill, 'FaceAlpha', 0.45, 'EdgeColor', 'none', ...
        'HandleVisibility', 'off');
end
for k = 1:numel(y)
    plot(ax, [baseStats(k), candStats(k)], [yBase(k), yCand(k)], '-', ...
        'Color', S.colors.grid, 'LineWidth', 2.2, ...
        'HandleVisibility', 'off');
end
hBase = plot(ax, baseStats, yBase, 's', ...
    'MarkerFaceColor', S.colors.background, ...
    'MarkerEdgeColor', S.colors.baseline, ...
    'MarkerSize', 6.4, 'LineWidth', 1.4, 'LineStyle', 'none', ...
    'DisplayName', 'FIFO baseline');
hCand = plot(ax, candStats, yCand, 'o', ...
    'MarkerFaceColor', S.colors.primary, ...
    'MarkerEdgeColor', S.colors.ink, ...
    'MarkerSize', 5.6, 'LineWidth', 0.7, 'LineStyle', 'none', ...
    'DisplayName', 'Bounded rolling exchange');
for k = 1:numel(y)
    text(ax, max(baseStats(k), candStats(k)) + xOffset, y(k), ...
        sprintf('%+.2f ms', deltaStats(k)), ...
        'Color', S.colors.ink, 'FontName', S.fontName, ...
        'FontSize', S.fontSize, 'FontWeight', 'normal', ...
        'HorizontalAlignment', 'left', 'VerticalAlignment', 'middle', ...
        'Interpreter', 'none', 'Clipping', 'on');
end
hold(ax, 'off');

mf_apply_axes(ax, S);
ax.YTick = y;
ax.YTickLabel = statLabels;
ax.YDir = 'reverse';
ax.YGrid = 'off';
ax.XMinorTick = 'off';
ylim(ax, [0.45, numel(y) + 0.45]);
xlim(ax, [0, xMax]);
ax.XTick = 0:20:(floor(xMax / 20) * 20);
xlabel(ax, 'Network latency (ms)');
ylabel(ax, 'Summary statistic');

if isfield(D, 'baselineTaskCount')
    nText = comma_integer(D.baselineTaskCount);
else
    nText = comma_integer(numel(baseRaw));
end
if isfield(D, 'baselineAtFiveMsPct')
    fifoFivePct = D.baselineAtFiveMsPct;
else
    fifoFivePct = 100 * mean(abs(baseRaw - 5) < 1e-12);
end
if isfield(D, 'baselineSlaViolationCount') && isfield(D, 'candidateSlaViolationCount')
    slaText = sprintf('SLA violations = %d/%s for both', ...
        D.baselineSlaViolationCount, nText);
else
    slaText = 'SLA violations = 0 for both';
end
text(ax, 0, 1.055, ...
    sprintf(['n = %s each  |  %s\n' ...
        'FIFO mass at 5 ms = %.2f%%  |  right labels = candidate - FIFO'], ...
        nText, slaText, fifoFivePct), ...
    'Units', 'normalized', 'HorizontalAlignment', 'left', ...
    'VerticalAlignment', 'bottom', 'Color', S.colors.ink, ...
    'FontName', S.fontName, 'FontSize', S.fontSize, ...
    'Clipping', 'off', 'Interpreter', 'none');
mf_legend(ax, S, [hBase, hCand], 'Location', 'northeast', ...
    'Orientation', 'horizontal', 'NumColumns', 2);

outputs = mf_export_triplet(fig, outputDir, "fig-q2-latency-ecdf", S);
close(fig);
end

function q = linear_percentile(x, p)
x = sort(x(:));
n = numel(x);
r = 1 + (n - 1) * p(:);
lo = floor(r);
hi = ceil(r);
w = r - lo;
q = (1 - w) .* x(lo) + w .* x(hi);
end

function value = comma_integer(n)
raw = sprintf('%d', round(n));
parts = {};
while numel(raw) > 3
    parts{end + 1} = raw(end - 2:end); %#ok<AGROW>
    raw = raw(1:end - 3);
end
parts{end + 1} = raw;
value = strjoin(fliplr(parts), ',');
end
