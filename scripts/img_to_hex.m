z% ==============================
% IMAGE TO HEX CONVERTER
% AUTO SIZE + HEIC SUPPORT
% ==============================

clc; clear; close all;

[file, path] = uigetfile( ...
{'*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.bmp;*.heic','Image Files'}, ...
'Select an Image');

if isequal(file,0)
    disp("No file selected.");
    return;
end

img_path = fullfile(path,file);
[~,name,ext] = fileparts(file);

% --- Handle HEIC ---
if strcmpi(ext,'.heic')

    disp("HEIC detected. Converting to PNG...");

    temp_png = fullfile(path,[name '_temp.png']);

    % Use system command (Windows)
    cmd = sprintf('magick "%s" "%s"', img_path, temp_png);
    system(cmd);

    img = imread(temp_png);

    delete(temp_png);

else
    img = imread(img_path);
end

% Show image
figure;
imshow(img);
title("Selected Image");

% Convert to grayscale if needed
if size(img,3) == 3
    img = rgb2gray(img);
end

% Detect dimensions automatically
[HEIGHT, WIDTH] = size(img);

fprintf("Width  : %d\n", WIDTH);
fprintf("Height : %d\n", HEIGHT);

% Create HEX file
hex_file = fullfile(path,[name '.hex']);
fid = fopen(hex_file,'w');

% Write HEX values
for r = 1:HEIGHT
    for c = 1:WIDTH
        fprintf(fid,'%02X\n', img(r,c));
    end
end

fclose(fid);

disp("HEX file generated successfully.");
disp(['Saved at: ', hex_file]);