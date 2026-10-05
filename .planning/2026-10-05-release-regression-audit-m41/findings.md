# Findings

- `v1.3.0rc3-isis9.0.0` exists as a non-draft prerelease with Linux cp312 and Windows cp312 wheelhouses plus `SHA256SUMS.txt`.
- `v1.4.0rc3-isis10.0.0` exists as a non-draft prerelease with Linux cp313 and Windows cp313 wheelhouses plus `SHA256SUMS.txt`.
- Both checksum files contain exactly two valid 64-hex SHA-256 entries, one per wheelhouse archive.
- Recorded hashes:
  - ISIS 9 Linux: `c110eb967bf9d5388357d2d26488999b24d6bce786c2b4415c8d66f28519daec`
  - ISIS 9 Windows: `57c761463cb6db967e90a743848ad7f76dded3d4055365119fa0a9951ade2fc2`
  - ISIS 10 Linux: `f2891770a13cf2bf8215c89358746ac594f11cb724e3ff5c79ac8cc6ca712ef6`
  - ISIS 10 Windows: `ed2da3c371c4924e9b50880fca18c0656732db3d36cf036e2b2738bb5c48be34`
- `packaging/releases/isis9.toml` and `isis10.toml` match the published tags and keep prerelease mode enabled.
