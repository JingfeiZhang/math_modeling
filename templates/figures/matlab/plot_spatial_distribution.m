function outputs = plot_spatial_distribution(inputCsv, outputDir, stem, xLabel, xUnit, yLabel, yUnit, valueLabel, valueUnit)
% Plot spatial values as a diverging change from an evidence-grounded baseline.
arguments
    inputCsv (1,1) string
    outputDir (1,1) string
    stem (1,1) string = "spatial-distribution"
    xLabel (1,1) string = "x"
    xUnit (1,1) string = "dimensionless"
    yLabel (1,1) string = "y"
    yUnit (1,1) string = "dimensionless"
    valueLabel (1,1) string = "Change"
    valueUnit (1,1) string = "dimensionless"
end
T = readtable(inputCsv, 'TextType', 'string');
mm_require_columns(T, {'x', 'y', 'value', 'baseline_value'});
x = mm_num(T, 'x');
y = mm_num(T, 'y');
value = mm_num(T, 'value');
baseline = mm_num(T, 'baseline_value');
delta = value - baseline;

fig = mm_publication_figure(15, 8.8);
ax = axes(fig);
scatter(ax, x, y, 38, delta, 'filled', 'MarkerFaceAlpha', 0.85);
axis(ax, 'equal');
grid(ax, 'on');
ax.GridAlpha = 0.15;
colormap(ax, [linspace(0.20, 0.98, 128)' linspace(0.42, 0.98, 128)' ones(128, 1); ones(128, 1) linspace(0.98, 0.35, 128)' linspace(0.98, 0.35, 128)']);
maxDelta = max(abs(delta));
if maxDelta == 0
    maxDelta = 1;
end
caxis(ax, [-maxDelta maxDelta]);
cb = colorbar(ax);
if valueUnit == "dimensionless"
    cb.Label.String = valueLabel;
else
    cb.Label.String = valueLabel + " (" + valueUnit + ")";
end
if xUnit == "dimensionless"
    xlabel(ax, xLabel);
else
    xlabel(ax, xLabel + " (" + xUnit + ")");
end
if yUnit == "dimensionless"
    ylabel(ax, yLabel);
else
    ylabel(ax, yLabel + " (" + yUnit + ")");
end
outputs = mm_export_triplet(fig, outputDir, stem);
close(fig);
end
