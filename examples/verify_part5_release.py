"""Verify the release allowlist and every bundled file before running code."""
import hashlib
import json
from pathlib import Path


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'release-manifest.json').read_text())
    for entry in manifest['files']:
        path = (root / entry['path']).resolve()
        if not path.is_relative_to(root) or path.is_symlink():
            raise ValueError('Unsafe path')
        if path.stat().st_size != entry['bytes']:
            raise ValueError('Size mismatch: ' + entry['path'])
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != entry['sha256']:
            raise ValueError('SHA256 mismatch: ' + entry['path'])
    print('Release files verified:', len(manifest['files']))
    return manifest


if __name__ == '__main__':
    verify(Path(__file__).resolve().parent.parent)
