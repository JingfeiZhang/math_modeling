function artifacts = exportModelingFigure(fig, basePath, varargin)
%EXPORTMODELINGFIGURE Export vector masters and a high-resolution PNG copy.

parser = inputParser;
addRequired(parser, 'fig');
addRequired(parser, 'basePath', @(x) ischar(x) || isstring(x));
addParameter(parser, 'Resolution', 400, @(x) isnumeric(x) && isscalar(x) && x >= 300);
parse(parser, fig, basePath, varargin{:});

basePath = char(parser.Results.basePath);
[outputDir, baseName] = fileparts(basePath);
if isempty(outputDir)
    outputDir = pwd;
end
if ~isfolder(outputDir)
    mkdir(outputDir);
end
basePath = fullfile(outputDir, baseName);

set(fig, 'Color', 'white', 'InvertHardcopy', 'off', 'Renderer', 'painters');
drawnow;

artifacts = struct();
artifacts.pdf = [basePath, '.pdf'];
artifacts.svg = [basePath, '.svg'];
artifacts.png = [basePath, '.png'];
token = char(java.util.UUID.randomUUID());
temporary = struct( ...
    'pdf', fullfile(outputDir, [baseName, '.', token, '.tmp.pdf']), ...
    'svg', fullfile(outputDir, [baseName, '.', token, '.tmp.svg']), ...
    'png', fullfile(outputDir, [baseName, '.', token, '.tmp.png']));
temporaryCleanup = onCleanup(@() cleanupTemporary(temporary)); %#ok<NASGU>
exportgraphics(fig, temporary.pdf, 'ContentType', 'vector', 'BackgroundColor', 'white');
exportgraphics(fig, temporary.svg, 'ContentType', 'vector', 'BackgroundColor', 'white');
exportgraphics(fig, temporary.png, 'Resolution', parser.Results.Resolution, 'BackgroundColor', 'white');
replaceArtifact(temporary.pdf, artifacts.pdf);
replaceArtifact(temporary.svg, artifacts.svg);
replaceArtifact(temporary.png, artifacts.png);

artifacts.pdfBytes = dir(artifacts.pdf).bytes;
artifacts.svgBytes = dir(artifacts.svg).bytes;
artifacts.pngBytes = dir(artifacts.png).bytes;
assert(all([artifacts.pdfBytes, artifacts.svgBytes, artifacts.pngBytes] > 0), ...
    'One or more exported figure files are empty.');
artifacts.hashManifest = fullfile(outputDir, [baseName, '.hashes.json']);
artifacts.hashes = hashFigureArtifacts(string(outputDir), string(baseName));
end

function replaceArtifact(source, destination)
lastMessage = '';
for attempt = 1:6
    [ok, message] = movefile(source, destination, 'f');
    if ok
        return;
    end
    lastMessage = message;
    pause(0.15 * attempt);
end
error('mathmodeling:FigureArtifactReplaceFailed', ...
    'Unable to replace figure artifact after retries: %s (%s)', destination, lastMessage);
end

function cleanupTemporary(temporary)
fields = fieldnames(temporary);
for index = 1:numel(fields)
    path = temporary.(fields{index});
    if isfile(path)
        delete(path);
    end
end
end
