function map = mf_colormap(kind, S, n)
% Build registered sequential or diverging maps by interpolation.
if nargin < 3
    n = 256;
end
switch string(kind)
    case "sequential"
        anchors = [S.colors.background; S.colors.auxiliary; S.colors.primary];
    case "diverging"
        anchors = [S.colors.primary; S.colors.fill; S.colors.risk];
    case "outcome"
        anchors = [S.colors.risk; S.colors.fill; S.colors.improved];
    otherwise
        error('matlabFigures:UnknownColormap', 'Unknown colormap kind: %s', kind);
end
x = linspace(0, 1, size(anchors, 1));
xi = linspace(0, 1, n);
map = interp1(x, anchors, xi, 'linear');
map = min(max(map, 0), 1);
end
