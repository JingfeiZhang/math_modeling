function outputs = mm_export_triplet(fig, outputDir, stem)
% Export a publication figure as vector PDF/SVG and 400 dpi PNG.
if ~isfolder(outputDir)
    mkdir(outputDir);
end
outputs = {fullfile(outputDir, stem + ".pdf"), fullfile(outputDir, stem + ".svg"), fullfile(outputDir, stem + ".png")};
exportgraphics(fig, outputs{1}, 'ContentType', 'vector', 'BackgroundColor', 'white');
exportgraphics(fig, outputs{2}, 'ContentType', 'vector', 'BackgroundColor', 'white');
exportgraphics(fig, outputs{3}, 'Resolution', 400, 'BackgroundColor', 'white');
end
