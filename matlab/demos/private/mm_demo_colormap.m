function colors = mm_demo_colormap(name, count, style)
%MM_DEMO_COLORMAP Return fixed, print-safe continuous maps.
arguments
    name (1,1) string
    count (1,1) double {mustBeInteger, mustBePositive} = 256
    style = []
end
if isempty(style)
    style = applyModelingStyle(axes('Visible', 'off'));
end
switch lower(name)
    case "sequential"
        anchors = [style.palette.background; style.palette.baseline; style.palette.primary];
    case "diverging"
        anchors = [style.palette.primary; style.palette.fill; style.palette.risk];
    otherwise
        error('mathmodeling:UnknownDemoColormap', 'Unknown demo colormap: %s', name);
end
positions = linspace(0, 1, size(anchors, 1));
colors = interp1(positions, anchors, linspace(0, 1, count), 'pchip');
colors = min(max(colors, 0), 1);
end
