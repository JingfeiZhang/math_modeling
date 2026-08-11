function manifest = hashFigureArtifacts(outputDir, stem)
%HASHFIGUREARTIFACTS Record provenance and deterministic visual hashes.
arguments
    outputDir (1,1) string
    stem (1,1) string
end

pdfPath = fullfile(outputDir, stem + ".pdf");
svgPath = fullfile(outputDir, stem + ".svg");
pngPath = fullfile(outputDir, stem + ".png");
required = [pdfPath, svgPath, pngPath];
for path = required
    if ~isfile(path)
        error('mathmodeling:MissingFigureArtifact', 'Missing figure artifact: %s', path);
    end
end

svgText = fileread(svgPath);
svgText = regexprep(svgText, '\r\n?', '\n');
svgText = regexprep(svgText, '(?s)<!--.*?-->', '');
svgText = regexprep(svgText, '(?is)<metadata\b.*?</metadata>', '');
svgText = regexprep(svgText, 'fillPattern[0-9]+_', 'fillPattern_');
svgText = regexprep(svgText, '[ \t]+(?=\n|$)', '');
svgCanonical = strtrim(svgText);

[pngImage, colorMap, alpha] = imread(pngPath);
if ~isempty(colorMap)
    rgb = uint8(round(255 * ind2rgb(pngImage, colorMap)));
elseif ndims(pngImage) == 2
    gray = mmToUint8(pngImage);
    rgb = repmat(gray, [1, 1, 3]);
else
    rgb = mmToUint8(pngImage(:, :, 1:3));
    if size(pngImage, 3) >= 4 && isempty(alpha)
        alpha = pngImage(:, :, 4);
    end
end
if isempty(alpha)
    alpha = uint8(255 * ones(size(rgb, 1), size(rgb, 2)));
else
    alpha = mmToUint8(alpha);
end
rgba = cat(3, rgb, alpha);
height = size(rgba, 1);
width = size(rgba, 2);
pixelHeader = unicode2native(sprintf('RGBA|%dx%d|uint8|', width, height), 'UTF-8');
pixelBytes = reshape(permute(rgba, [3, 2, 1]), 1, []);

manifest = struct();
manifest.schema_version = 1;
manifest.stem = char(stem);
manifest.artifacts = struct();
manifest.artifacts.pdf = mmRawRecord(pdfPath);
manifest.artifacts.pdf.determinism_role = 'provenance-only';
manifest.artifacts.svg = mmRawRecord(svgPath);
manifest.artifacts.svg.canonical_sha256 = mmSha256(unicode2native(svgCanonical, 'UTF-8'));
manifest.artifacts.svg.canonicalization = 'utf8-lf-no-comments-no-metadata-fillpattern-normalized-rstrip';
manifest.artifacts.png = mmRawRecord(pngPath);
manifest.artifacts.png.pixel_sha256 = mmSha256([pixelHeader, pixelBytes]);
manifest.artifacts.png.pixel_encoding = sprintf('RGBA|%dx%d|uint8|row-major', width, height);
manifest.reproducibility_note = [ ...
    'PDF raw SHA-256 is retained for provenance, but export metadata may change raw bytes. ', ...
    'Use canonical SVG SHA-256 and decoded PNG pixel SHA-256 as deterministic visual checks.' ...
];

manifestPath = fullfile(outputDir, stem + ".hashes.json");
fileId = fopen(manifestPath, 'w', 'n', 'UTF-8');
assert(fileId >= 0, 'Unable to write hash manifest: %s', manifestPath);
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, jsonencode(manifest, PrettyPrint=true), 'char');
end

function record = mmRawRecord(path)
info = dir(path);
record = struct('path', char(path), 'bytes', info.bytes, ...
    'raw_sha256', mmSha256(mmReadBytes(path)));
end

function bytes = mmReadBytes(path)
fileId = fopen(path, 'rb');
assert(fileId >= 0, 'Unable to read artifact: %s', path);
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId, Inf, '*uint8').';
end

function hex = mmSha256(bytes)
digest = java.security.MessageDigest.getInstance('SHA-256');
digest.update(typecast(uint8(bytes(:)), 'int8'));
raw = typecast(digest.digest(), 'uint8');
hex = lower(reshape(dec2hex(raw, 2).', 1, []));
end

function value = mmToUint8(value)
if isa(value, 'uint8')
    return;
elseif isa(value, 'uint16')
    value = uint8(round(double(value) / 257));
elseif islogical(value)
    value = uint8(value) * 255;
else
    value = uint8(round(255 * min(max(double(value), 0), 1)));
end
end
