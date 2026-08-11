function mf_apply_axes(ax, S)
% Apply restrained publication axes without an in-figure title.
ax.FontName = S.fontName;
ax.FontSize = S.fontSize;
ax.LabelFontSizeMultiplier = 1;
ax.TitleFontSizeMultiplier = 1;
ax.LineWidth = 0.7;
ax.XColor = S.colors.ink;
ax.YColor = S.colors.ink;
ax.Color = S.colors.background;
ax.Box = 'off';
ax.TickDir = 'out';
ax.TickLength = [0.012, 0.012];
ax.XGrid = 'on';
ax.YGrid = 'on';
ax.GridColor = S.colors.grid;
ax.GridAlpha = S.gridAlpha;
ax.MinorGridAlpha = 0;
ax.TickLabelInterpreter = 'none';
ax.XAxis.Exponent = 0;
ax.YAxis.Exponent = 0;
ax.Clipping = 'on';
end
