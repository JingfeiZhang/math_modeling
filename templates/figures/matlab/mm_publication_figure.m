function fig = mm_publication_figure(widthCm, heightCm)
% Use explicit handles and stable dimensions for reproducible exports.
fig = figure('Visible', 'off', 'Color', 'white', 'Units', 'centimeters', ...
    'Position', [2 2 widthCm heightCm], 'PaperPositionMode', 'auto');
set(fig, 'DefaultAxesFontName', 'Arial', 'DefaultAxesFontSize', 8.5, ...
    'DefaultTextFontName', 'Arial', 'DefaultTextFontSize', 8.5);
end
