function S = mf_style()
% Project publication style: journal-spectrum-v2 only.
S.paletteId = "journal-spectrum-v2";
S.fontName = "Times New Roman";
S.fontSize = 8.5;
S.legendFontSize = 8;
S.minFontSize = 8;
S.lineWidth = 1.5;
S.referenceLineWidth = 0.8;
S.markerSize = 4.2;
S.gridAlpha = 0.18;
S.bandAlpha = 0.11;
S.widthCm = 15.8;
S.heightCm = 10.4;
S.heightTallCm = 11.2;
S.pngDpi = 400;

S.colors.primary = hex2rgb("#5292F7");
S.colors.baseline = hex2rgb("#79CAFB");
S.colors.improved = hex2rgb("#4EA660");
S.colors.highlight = hex2rgb("#F7A24F");
S.colors.risk = hex2rgb("#E95351");
S.colors.auxiliary = hex2rgb("#AA77E9");
S.colors.accent = hex2rgb("#CC247C");
S.colors.caution = hex2rgb("#FBEB66");
S.colors.ink = hex2rgb("#1F2933");
S.colors.grid = hex2rgb("#D9DEE5");
S.colors.fill = hex2rgb("#EAF0F4");
S.colors.background = hex2rgb("#FFFFFF");

hex = ["#CC247C", "#E95351", "#F7A24F", "#FBEB66", ...
    "#4EA660", "#79CAFB", "#5292F7", "#AA77E9"];
S.categorical = zeros(numel(hex), 3);
for k = 1:numel(hex)
    S.categorical(k, :) = hex2rgb(hex(k));
end
end

function rgb = hex2rgb(value)
value = char(erase(string(value), "#"));
rgb = [hex2dec(value(1:2)), hex2dec(value(3:4)), hex2dec(value(5:6))] / 255;
end
