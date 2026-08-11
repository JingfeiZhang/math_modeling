function hex = mm_demo_sha256(path)
%MM_DEMO_SHA256 Return the SHA-256 digest of a file.
fileId = fopen(path, 'rb');
assert(fileId >= 0, 'Unable to hash artifact: %s', path);
cleanup = onCleanup(@() fclose(fileId)); %#ok<NASGU>
bytes = fread(fileId, Inf, '*uint8').';
digest = java.security.MessageDigest.getInstance('SHA-256');
digest.update(typecast(uint8(bytes(:)), 'int8'));
raw = typecast(digest.digest(), 'uint8');
hex = lower(reshape(dec2hex(raw, 2).', 1, []));
end
