function outputs = plot_model_flowchart(inputCsv, outputDir, stem)
% Plot an editable graph of the actual model/data flow declared in a CSV.
arguments
    inputCsv (1,1) string
    outputDir (1,1) string
    stem (1,1) string = "model-flowchart"
end
T = readtable(inputCsv, 'TextType', 'string');
mm_require_columns(T, {'source', 'target'});
source = string(T.source);
target = string(T.target);
if any(strlength(strtrim(source)) == 0 | strlength(strtrim(target)) == 0)
    error('mathmodeling:MissingNode', 'Flowchart node labels must be non-empty.');
end
G = digraph(source, target);
if numnodes(G) == 0
    error('mathmodeling:EmptyGraph', 'Flowchart evidence contains no nodes.');
end

fig = mm_publication_figure(15, 8.2);
ax = axes(fig);
p = plot(ax, G, 'Layout', 'layered', 'ArrowSize', 12, 'LineWidth', 1.1, ...
    'NodeColor', [59 111 182] / 255, 'EdgeColor', [107 114 128] / 255, ...
    'MarkerSize', 8, 'NodeFontSize', 8.5);
p.NodeLabel = G.Nodes.Name;
axis(ax, 'off');
title(ax, 'Model structure and actual data flow');
outputs = mm_export_triplet(fig, outputDir, stem);
close(fig);
end
