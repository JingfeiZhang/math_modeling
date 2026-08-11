function outputs = fig_q4_scenario_tradeoff(D, outputDir, S)
fig = mf_publication_figure(S);
ax = axes(fig, 'Position', [0.18, 0.22, 0.62, 0.66]);
score = double(D.normalizedImprovement);
imagesc(ax, 1:size(score, 2), 1:size(score, 1), score);
set(ax, 'YDir', 'normal');
colormap(ax, mf_colormap("outcome", S));
clim(ax, [-1, 1]);
mf_apply_axes(ax, S);
ax.XGrid = 'off';
ax.YGrid = 'off';
xlim(ax, [0.5, size(score, 2) + 0.5]);
ylim(ax, [0.5, size(score, 1) + 0.5]);
ax.XTick = 1:4;
ax.XTickLabel = {sprintf('Net cost\n(kCNY)'), ...
    sprintf('Purchase carbon\n(tCO2)'), ...
    sprintf('Renewable use\n(pp)'), sprintf('Positive peak\n(MW)')};
ax.YTick = 1:numel(D.scenarioLabels);
ax.YTickLabel = cellstr(D.scenarioLabels);
ylabel(ax, 'Scenario');

delta = double(D.deltaValues);
for row = 1:size(delta, 1)
    labels = {format_delta(delta(row, 1), 1, 'kCNY'), ...
        format_delta(delta(row, 2), 2, 'tCO2'), ...
        format_delta(delta(row, 3), 3, 'pp'), ...
        format_delta(delta(row, 4), 1, 'MW')};
    for column = 1:size(delta, 2)
        labelColor = S.colors.ink;
        if abs(score(row, column)) >= 0.68
            labelColor = S.colors.background;
        end
        text(ax, column, row, labels{column}, ...
            'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle', ...
            'FontName', S.fontName, 'FontSize', S.legendFontSize, ...
            'FontWeight', 'bold', 'Color', labelColor, ...
            'Interpreter', 'none');
    end
end
cb = mf_colorbar(ax, S, 'Within-metric normalized improvement');
cb.Ticks = [-1, 0, 1];
cb.TickLabels = {'Worse', 'No change', 'Better'};
outputs = mf_export_triplet(fig, outputDir, "fig-q4-scenario-tradeoff", S);
close(fig);
end

function label = format_delta(value, digits, unit)
if value == 0
    number = sprintf(['%0.', num2str(digits), 'f'], value);
else
    number = sprintf(['%+0.', num2str(digits), 'f'], value);
end
label = [number, ' ', unit];
end
