function value = mf_sha256(path)
% Return a lowercase SHA-256 digest for a file.
fid = fopen(path, 'rb');
if fid < 0
    error('matlabFigures:HashOpenFailed', 'Cannot open file for hashing: %s', path);
end
cleanup = onCleanup(@() fclose(fid));
bytes = fread(fid, Inf, '*uint8');
md = java.security.MessageDigest.getInstance('SHA-256');
md.update(typecast(bytes, 'int8'));
digest = typecast(md.digest(), 'uint8');
value = lower(string(reshape(dec2hex(digest, 2).', 1, [])));
clear cleanup;
end
