function outputs = fig_q1_schedule_gantt(T, outputDir, S)
fig = mf_publication_figure(S, S.heightTallCm);
ax = axes(fig, 'Position', [0.15, 0.23, 0.81, 0.65]);
regions = sort(unique(string(T.ExecutionRegion)));
taskTypes = unique(string(T.TaskType), 'stable');
taskLabels = taskTypes;
taskLabels(taskTypes == "AITraining") = "Training";
startHour = double(T.StartMinute) / 60;
endHour = double(T.EndMinute) / 60;
gpu = double(T.GPU_Demand);
x0 = 2376;
x1 = 2400;
inWindow = endHour > x0 & startHour < x1;
maxGpu = max(gpu(inWindow), [], 'omitnan');
if isempty(maxGpu) || maxGpu <= 0
    maxGpu = 1;
end
hold(ax, 'on');
for k = find(inWindow).'
    regionIndex = find(regions == string(T.ExecutionRegion(k)), 1);
    laneOffset = 0.32 * (mod(double(T.TaskID(k)), 13) / 12 - 0.5);
    y = regionIndex + laneOffset;
    taskIndex = find(taskTypes == string(T.TaskType(k)), 1);
    color = S.categorical(taskIndex, :);
    width = 0.45 + 1.25 * sqrt(max(gpu(k), 0) / maxGpu);
    startRelative = max(startHour(k) - x0, 0);
    endRelative = min(endHour(k) - x0, 24);
    plot(ax, [startRelative, endRelative], [y, y], '-', ...
        'Color', color, 'LineWidth', width, 'HandleVisibility', 'off');
    if startHour(k) < x0
        plot(ax, 0, y, 'd', 'Color', S.colors.ink, ...
            'MarkerSize', 2.7, 'LineWidth', 0.5, 'HandleVisibility', 'off');
    end
    if endHour(k) > x1
        plot(ax, 24, y, '>', 'Color', S.colors.ink, ...
            'MarkerSize', 2.7, 'LineWidth', 0.5, 'HandleVisibility', 'off');
    end
end
for t = 1:numel(taskTypes)
    plot(ax, NaN, NaN, '-', 'Color', S.categorical(t, :), 'LineWidth', 2.2, ...
        'DisplayName', strrep(taskLabels(t), '_', ' '));
end
plot(ax, NaN, NaN, 'd', 'Color', S.colors.ink, 'MarkerFaceColor', S.colors.background, ...
    'MarkerSize', 3.4, 'LineWidth', 0.6, 'DisplayName', 'Carry-in continuation');
plot(ax, NaN, NaN, '>', 'Color', S.colors.ink, 'MarkerFaceColor', S.colors.background, ...
    'MarkerSize', 3.4, 'LineWidth', 0.6, 'DisplayName', 'Continues to closeout');
hold(ax, 'off');
mf_apply_axes(ax, S);
ax.YGrid = 'off';
xlim(ax, [0, 24]);
ylim(ax, [0.5, numel(regions) + 0.5]);
ax.XTick = 0:6:24;
ax.YTick = 1:numel(regions);
ax.YTickLabel = cellstr(replace(regions, "Region", "Region "));
xlabel(ax, 'Elapsed hour in final scheduling day');
ylabel(ax, 'Execution region');
mf_legend(ax, S, 'Location', 'southoutside', 'Orientation', 'horizontal', ...
    'NumColumns', 3);
outputs = mf_export_triplet(fig, outputDir, "fig-q1-schedule-gantt", S);
close(fig);
end
