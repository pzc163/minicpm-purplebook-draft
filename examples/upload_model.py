"""Explicit user-run upload to an already-created ModelScope repository."""
import argparse
from getpass import getpass
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--repo',required=True)
    p.add_argument('--folder',required=True)
    p.add_argument('--revision',required=True)
    a=p.parse_args()
    folder=Path(a.folder).resolve()
    if not folder.is_dir() or not (folder/'README.md').is_file():
        raise ValueError('stage only releasable files plus model card in a dedicated directory')
    from modelscope.hub.api import HubApi
    hub=HubApi()
    hub.login(getpass('ModelScope access token (hidden): '))
    hub.upload_folder(repo_id=a.repo,folder_path=str(folder),revision=a.revision,
                      commit_message='Upload reproducible MiniCPM cookbook checkpoint')
    print('Uploaded. Record the actual revision / commit from your repository page.')
