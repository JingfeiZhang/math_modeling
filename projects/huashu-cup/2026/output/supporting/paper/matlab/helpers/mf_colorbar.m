function cb = mf_colorbar(ax, S, labelText)
% Add an external colorbar without shrinking the declared plotting area.
plotPosition = ax.Position;
cb = colorbar(ax, 'eastoutside');
ax.Position = plotPosition;
cb.Position = [plotPosition(1) + plotPosition(3) + 0.025, ...
    plotPosition(2), 0.020, plotPosition(4)];
cb.FontName = S.fontName;
cb.FontSize = S.legendFontSize;
cb.Color = S.colors.ink;
cb.LineWidth = 0.7;
cb.TickDirection = 'out';
cb.Label.String = labelText;
cb.Label.FontName = S.fontName;
cb.Label.FontSize = S.legendFontSize;
cb.Label.Color = S.colors.ink;
cb.Label.Interpreter = 'none';
end
