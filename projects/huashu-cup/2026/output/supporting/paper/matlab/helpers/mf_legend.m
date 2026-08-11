function lgd = mf_legend(ax, S, varargin)
% Create a consistent high-contrast legend.
lgd = legend(ax, varargin{:});
lgd.FontName = S.fontName;
lgd.FontSize = S.legendFontSize;
lgd.TextColor = S.colors.ink;
lgd.Color = 'none';
lgd.Box = 'off';
lgd.Interpreter = 'none';
end
