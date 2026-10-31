"""Configure the public entry point without editing application or private settings."""
import re,shlex
from pathlib import Path
REPOSITORY=re.compile(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*')
VERSION=re.compile(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9][A-Za-z0-9.-]*)?')
def validate(repository,version):
    if not REPOSITORY.fullmatch(repository):raise ValueError('Repository must be OWNER/REPOSITORY, without a URL.')
    if not VERSION.fullmatch(version):raise ValueError('Use an exact VERSION without a leading v.')
def render(root,repository,version):
    validate(repository,version)
    text=(root/'setup.sh').read_text()
    for marker,value in [("DEFAULT_REPOSITORY=''",repository),("DEFAULT_VERSION=''",version)]:
        if text.count(marker)!=1:raise ValueError('Unexpected setup.sh layout')
        text=text.replace(marker,marker[:-2]+shlex.quote(value),1)
    return text

def command(repository,version,role='controller'):
    validate(repository,version)
    if role not in ('controller','receiver'):raise ValueError('Invalid role')
    url=f'https://github.com/{repository}/releases/download/v{version}/hnls-setup.sh'
    return f'curl -fsSL {shlex.quote(url)} | bash'+(' -s -- --role receiver' if role=='receiver' else '')
