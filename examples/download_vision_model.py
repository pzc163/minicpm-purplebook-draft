"""Download a fixed ModelScope Git commit and verify every file's SHA256.

ModelScope 1.33.0 snapshot_download validates revisions against tags/branches,
while the file listing and resolve endpoints accept a full Git commit.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import time
from urllib.parse import quote

MODEL_ID = 'OpenBMB/MiniCPM-V-4.6'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download_fixed(revision, output):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Use the full 40-character Git commit, not a mutable branch')
    from modelscope.hub.api import HubApi
    import requests
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    files = HubApi().get_model_files(MODEL_ID, revision=revision, recursive=True)
    entries = [entry for entry in files if entry.get('Type') == 'blob']
    if not entries:
        raise ValueError('No model files at the requested commit')
    manifest = []
    for entry in entries:
        relative = PurePosixPath(entry['Path'])
        if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative):
            raise ValueError('Unsafe repository file path')
        expected = entry.get('Sha256', '').lower()
        if not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise ValueError(f'Missing SHA256: {relative}')
        size = int(entry['Size'])
        target = output.joinpath(*relative.parts)
        if not target.resolve().is_relative_to(output):
            raise ValueError('File path escapes the model directory')
        target.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://www.modelscope.cn/models/{MODEL_ID}/resolve/{revision}/{quote(str(relative), safe="/")}'
        if not (target.is_file() and target.stat().st_size == size and sha256(target) == expected):
            temporary = target.with_name(target.name + '.part')
            print(f'Downloading {relative}: {size / 1024**2:.1f} MiB', flush=True)
            for attempt in range(3):
                try:
                    digest = hashlib.sha256()
                    with requests.get(url, stream=True, timeout=(30, 180)) as response:
                        response.raise_for_status()
                        with temporary.open('wb') as stream:
                            for chunk in response.iter_content(1024 * 1024):
                                if chunk:
                                    stream.write(chunk)
                                    digest.update(chunk)
                    if temporary.stat().st_size != size or digest.hexdigest() != expected:
                        raise ValueError(f'Size or SHA256 mismatch: {relative}')
                    temporary.replace(target)
                    break
                except (requests.RequestException, ValueError):
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)
        print(f'Verified {relative}', flush=True)
        manifest.append({'path': str(relative), 'size_bytes': size, 'sha256': expected,
                         'file_revision': entry.get('Revision'), 'source_url': url})
    (output / 'download-manifest.json').write_text(json.dumps({
        'model_id': MODEL_ID, 'git_commit': revision,
        'verified_at': datetime.now(timezone.utc).isoformat(), 'files': manifest,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', required=True)
    parser.add_argument('--out', type=Path, default=Path('models/minicpm-v-4.6'))
    args = parser.parse_args()
    print(download_fixed(args.revision, args.out))
