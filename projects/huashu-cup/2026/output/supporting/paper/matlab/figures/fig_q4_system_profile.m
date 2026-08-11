function outputs = fig_q4_system_profile(D, outputDir, S)
% Show the sparse joint response without letting zero hours dominate the figure.
fig = mf_publication_figure(S, 9.2);
layout = tiledlayout(fig, 2, 1, ...
    'TileSpacing', 'compact', 'Padding', 'compact');

hours = double(D.hour(:));
aiDelta = double(D.deltaAiItMW(:));
gridDelta = double(D.deltaNetGridImportMW(:));
eventMask = max(abs([aiDelta, gridDelta]), [], 2) > 1e-9;
eventHours = hours(eventMask);
if isempty(eventHours)
    error('matlabFigures:Q4NoEvents', ...
        'The candidate and sequential baseline have no nonzero hourly differences.');
end

% Preserve true temporal spacing while omitting the unchanged leading interval.
xLimits = [max(min(hours), min(eventHours) - 0.75), ...
    min(max(hours) + 1, max(eventHours) + 0.75)];
xTicks = choose_event_ticks(eventHours, 7);

ax1 = nexttile(layout, 1);
hold(ax1, 'on');
yline(ax1, 0, '-', 'Color', S.colors.ink, ...
    'LineWidth', S.referenceLineWidth, 'HandleVisibility', 'off');
bar(ax1, eventHours, aiDelta(eventMask), 0.68, ...
    'FaceColor', S.colors.risk, 'EdgeColor', S.colors.ink, ...
    'LineWidth', 0.45, 'HandleVisibility', 'off');
hAi = plot(ax1, NaN, NaN, 's', 'LineStyle', 'none', ...
    'MarkerSize', 5.2, 'MarkerFaceColor', S.colors.risk, ...
    'MarkerEdgeColor', S.colors.ink, 'DisplayName', 'Delta AI IT load');
hGrid = plot(ax1, NaN, NaN, 's', 'LineStyle', 'none', ...
    'MarkerSize', 5.2, 'MarkerFaceColor', S.colors.primary, ...
    'MarkerEdgeColor', S.colors.ink, 'DisplayName', 'Delta net grid import');
hold(ax1, 'off');
mf_apply_axes(ax1, S);
ax1.XGrid = 'off';
ax1.XTickLabel = {};
xlim(ax1, xLimits);
ax1.XTick = xTicks;
ylim(ax1, padded_limits(aiDelta(eventMask), 0.12));
ylabel(ax1, 'Delta AI IT load (MW)');
text(ax1, 0.012, 0.90, '(a)', 'Units', 'normalized', ...
    'FontWeight', 'bold', 'Color', S.colors.ink);

ax2 = nexttile(layout, 2);
hold(ax2, 'on');
yline(ax2, 0, '-', 'Color', S.colors.ink, ...
    'LineWidth', S.referenceLineWidth, 'HandleVisibility', 'off');
bar(ax2, eventHours, gridDelta(eventMask), 0.68, ...
    'FaceColor', S.colors.primary, 'EdgeColor', S.colors.ink, ...
    'LineWidth', 0.45, 'HandleVisibility', 'off');
gridEvents = find(abs(gridDelta) > 1e-9);
for k = 1:numel(gridEvents)
    row = gridEvents(k);
    text(ax2, hours(row) + 0.48, gridDelta(row), ...
        sprintf('%+.1f', gridDelta(row)), ...
        'HorizontalAlignment', 'left', 'VerticalAlignment', 'middle', ...
        'FontName', S.fontName, 'FontSize', S.legendFontSize, ...
        'FontWeight', 'bold', 'Color', S.colors.ink, ...
        'Interpreter', 'none');
end
hold(ax2, 'off');
mf_apply_axes(ax2, S);
ax2.XGrid = 'off';
xlim(ax2, xLimits);
ax2.XTick = xTicks;
ylim(ax2, padded_limits(gridDelta(eventMask), 0.16));
xlabel(ax2, 'Relative hour in 2328-2399 window');
ylabel(ax2, 'Delta net grid import (MW)');
text(ax2, 0.012, 0.76, '(b)', 'Units', 'normalized', ...
    'FontWeight', 'bold', 'Color', S.colors.ink);
linkaxes([ax1, ax2], 'x');

lgd = legend(ax1, [hAi, hGrid], ...
    {'Delta AI IT load', 'Delta net grid import'}, ...
    'Location', 'northoutside', 'Orientation', 'horizontal', ...
    'NumColumns', 2, 'Box', 'off', 'FontName', S.fontName, ...
    'FontSize', S.legendFontSize, 'TextColor', S.colors.ink, ...
    'Interpreter', 'none');
lgd.Layout.Tile = 'north';

outputs = mf_export_triplet(fig, outputDir, "fig-q4-system-profile", S);
close(fig);
end

function ticks = choose_event_ticks(eventHours, maxTicks)
eventHours = unique(eventHours(:), 'stable');
if numel(eventHours) <= maxTicks
    ticks = eventHours.';
    return;
end
breaks = [1; find(diff(eventHours) > 1) + 1; numel(eventHours) + 1];
ticks = zeros(0, 1);
runLengths = zeros(numel(breaks) - 1, 1);
for k = 1:(numel(breaks) - 1)
    run = eventHours(breaks(k):(breaks(k + 1) - 1));
    ticks = [ticks; run(1); run(end)]; %#ok<AGROW>
    runLengths(k) = numel(run);
end
ticks = unique(ticks, 'stable');
while numel(ticks) < maxTicks
    [~, order] = sort(runLengths, 'descend');
    added = false;
    for k = order.'
        run = eventHours(breaks(k):(breaks(k + 1) - 1));
        candidate = run(ceil(numel(run) / 2));
        if ~ismember(candidate, ticks)
            ticks(end + 1, 1) = candidate; %#ok<AGROW>
            added = true;
            break;
        end
        runLengths(k) = 0;
    end
    if ~added
        break;
    end
end
ticks = sort(ticks).';
end

function limits = padded_limits(values, fraction)
values = values(isfinite(values));
lo = min([values; 0]);
hi = max([values; 0]);
span = hi - lo;
if span <= 0
    span = max(abs([lo; hi; 1]));
end
limits = [lo - fraction * span, hi + fraction * span];
end
