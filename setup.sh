#!/usr/bin/env bash
# HNLS download-and-install entry point. Published releases fill these defaults.
set -euo pipefail
DEFAULT_REPOSITORY=''
DEFAULT_VERSION=''
repository="$DEFAULT_REPOSITORY"
version="$DEFAULT_VERSION"
role=''
check_only=false
usage() {
    cat <<'HELP'
HNLS quick installation
  --repo OWNER/REPOSITORY   GitHub repository (baked into published installer)
  --version VERSION        Exact release version, without the leading v
  --role controller        Main Pi / web interface (default)
  --role receiver          Additional Pi / LED receiver
  --check                  Download and verify only; do not install
  -h, --help               Show this help

Fresh Raspberry Pi installations only. Existing HNLS/MLSC installs are refused.
Published installer assets already contain the repository and release version.
HELP
}
while (($#)); do
    case "$1" in
        --repo|--version|--role)
            if (($# < 2)); then echo "Missing value for $1" >&2; exit 2; fi
            case "$1" in --repo) repository="$2";; --version) version="$2";; --role) role="$2";; esac
            shift 2;;
        --check) check_only=true; shift;;
        -h|--help) usage; exit 0;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2;;
    esac
done
if [[ ! "$repository" =~ ^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    echo 'This source installer needs --repo OWNER/REPOSITORY. The published installer supplies it automatically.' >&2; exit 2
fi
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9][A-Za-z0-9.-]*)?$ ]]; then
    echo 'Use --version with an exact release number, for example the VERSION from the downloaded source.' >&2; exit 2
fi
if [[ -z "$role" ]]; then
    role=controller
    if [[ "$check_only" == false ]] && { exec 3</dev/tty; } 2>/dev/null; then
        printf 'Install HNLS as: 1) Main Pi  2) Additional Pi [1]: ' >/dev/tty
        IFS= read -r answer <&3 || answer=''
        exec 3<&-
        case "$answer" in ''|1) role=controller;; 2) role=receiver;; *) echo 'Choose 1 or 2, or use --role controller / receiver.' >&2; exit 2;; esac
    fi
fi
case "$role" in controller|receiver) ;; *) echo 'Role must be controller or receiver.' >&2; exit 2;; esac
if [[ "$check_only" == false ]]; then
    if [[ "$role" == controller ]]; then
        conflicts=(/share/music_led_strip_control /share/.venv /share/.mlsc /etc/systemd/system/mlsc.service /usr/lib/systemd/system/mlsc.service /lib/systemd/system/mlsc.service)
    else
        conflicts=(/opt/mlsc-receiver /etc/mlsc-receiver /etc/systemd/system/mlsc-receiver.service /usr/lib/systemd/system/mlsc-receiver.service /lib/systemd/system/mlsc-receiver.service)
    fi
    for target in "${conflicts[@]}"; do
        if [[ -e "$target" || -L "$target" ]]; then
            echo "Existing HNLS/MLSC installation found: $target. Nothing changed. Use a matching HNLS update instead." >&2; exit 1
        fi
    done
fi
for command in curl python3 mktemp; do
    if ! command -v "$command" >/dev/null; then echo "Required command missing: $command" >&2; exit 1; fi
done
umask 077
work=$(mktemp -d -t hnls-install.XXXXXXXX)
trap 'rm -rf -- "$work"' EXIT
asset="HNLS-${version}-source.zip"
base="https://github.com/${repository}/releases/download/v${version}"
printf 'Downloading HNLS %s (%s)…\n' "$version" "$role"
curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fsSL --retry 2 --max-time 300 --max-filesize 67108864 "$base/$asset" -o "$work/$asset"
curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fsSL --retry 2 --max-time 60 --max-filesize 1048576 "$base/SHA256SUMS.txt" -o "$work/SHA256SUMS.txt"
python3 - "$work" "$asset" "$version" <<'PY'
import hashlib,re,stat,sys,zipfile
from pathlib import Path,PurePosixPath
folder=Path(sys.argv[1]);asset=sys.argv[2];version=sys.argv[3]
lines=(folder/'SHA256SUMS.txt').read_text().splitlines()
matches=[line.split('  ',1)[0] for line in lines if line.endswith('  '+asset)]
if len(matches)!=1 or not re.fullmatch('[0-9a-f]{64}',matches[0]):raise SystemExit('Release checksum is missing, duplicated or invalid; nothing installed.')
archive=folder/asset
if hashlib.sha256(archive.read_bytes()).hexdigest()!=matches[0]:raise SystemExit('Release checksum mismatch; nothing installed.')
with zipfile.ZipFile(archive) as z:
    entries=z.infolist();seen=set();size=0
    if len(entries)>10000:raise SystemExit('Archive contains too many entries.')
    for info in entries:
        name=info.filename;p=PurePosixPath(name);kind=stat.S_IFMT(info.external_attr>>16)
        if not name or '\\' in name or p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0]!='HNLS' or len(p.parts)<2 or name in seen or kind not in (0,stat.S_IFREG,stat.S_IFDIR):
            raise SystemExit('Unsafe release archive entry; nothing installed.')
        if str(p)!=name.rstrip('/') or info.flag_bits&1:raise SystemExit('Invalid archive entry; nothing installed.')
        seen.add(name);size+=info.file_size
        if size>256*1024*1024:raise SystemExit('Expanded archive is too large.')
    if z.read('HNLS/VERSION').decode().strip()!=version:raise SystemExit('Release version does not match the installer.')
    for required in ('install.py','install.sh','release-manifest.json'):
        if 'HNLS/'+required not in seen:raise SystemExit('Incomplete HNLS release.')
    z.extractall(folder)
print('Release download verified.')
PY
python3 "$work/HNLS/install.py" --check
if [[ "$check_only" == true ]]; then
    echo 'Download and payload checks passed. No packages, services or application files were installed.'
    exit 0
fi
# Read sudo authentication from the terminal even when this script arrived over stdin.
if ((EUID == 0)); then
    python3 "$work/HNLS/install.py" --role "$role"
else
    sudo python3 "$work/HNLS/install.py" --role "$role"
fi
