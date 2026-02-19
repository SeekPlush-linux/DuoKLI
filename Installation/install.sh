#!/usr/bin/env bash
set -euo pipefail

GITHUB_REPO=""
DEFAULT_LOCATION="/usr/local/lib/duokli"
DOWNLOAD_DIR=""
BIN_DIR="/usr/local/bin"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--location DIR] [--tag TAG] [--uninstall] --github-repo owner/repo

Options:
  --location DIR       Install to custom location (default: ${DEFAULT_LOCATION})
  --github-repo REPO   GitHub repo in owner/repo format (required)
  --download-dir DIR   Temp download directory (default: current dir)
  --tag TAG            Specific release tag instead of latest
  --uninstall          Uninstall DuoKLI
  -h, --help           Show this help
EOF
}

BLUE="\033[1;34m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

die() { printf "%b✖%b %s\n" "${RED}" "${RESET}" "$*" >&2; exit 1; }
info() { printf "%b➜%b %s\n" "${GREEN}" "${RESET}" "$*"; }
note() { printf "%bℹ%b %s\n" "${BLUE}" "${RESET}" "$*"; }

check_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing: $1"
}

cleanup() {
  [[ -e "${ARCHIVE}" ]] && sudo rm -f "${ARCHIVE}" || true
}

OS_NAME=$(uname -s 2>/dev/null || echo unknown)
case "${OS_NAME}" in
  Linux|Darwin) :;;
  MINGW*|MSYS*|CYGWIN*) note "Windows detected; attempting WSL-compatible install";;
  *) note "Unrecognized platform ${OS_NAME}; continuing";;
esac

check_cmd curl
check_cmd tar
check_cmd python3

LOCATION="${DEFAULT_LOCATION}"
TAG=""
UNINSTALL=0

while [[ ${#} -gt 0 ]]; do
  case "$1" in
    --location)
      LOCATION="$2"; shift 2;;
    --github-repo)
      GITHUB_REPO="$2"; shift 2;;
    --download-dir)
      DOWNLOAD_DIR="$2"; shift 2;;
    --tag)
      TAG="$2"; shift 2;;
    --uninstall)
      UNINSTALL=1; shift;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

BIN_PATH="${BIN_DIR}/duokli"

if [[ ${UNINSTALL} -eq 1 ]]; then
  read -rp "Are you sure you want to uninstall DuoKLI? This operation will also delete your config permanently! [y/N]: " CONFIRM
  if [[ "${CONFIRM}" = "y" ]]; then
    info "Uninstalling"
    [[ -f "${BIN_PATH}" ]] && sudo rm -f "${BIN_PATH}" && note "Removed wrapper ${BIN_PATH}"
    [[ -d "${LOCATION}" ]] && sudo rm -rf "${LOCATION}" && note "Removed DuoKLI ${LOCATION}"
    info "Done"
    exit 0
  fi
  exit 1
fi

[[ -z "${GITHUB_REPO}" ]] && die "--github-repo owner/repo required"

if [[ -d "${LOCATION}" ]]; then
  read -rp "You have an existing installation of DuoKLI on your device, continuing will permanently delete it and install a fresh copy of DuoKLI. Would you like to continue? [y/N]: " CONFIRM
  if [[ "${CONFIRM}" != "y" ]]; then
    exit 1
  fi
fi

API_URL="https://api.github.com/repos/${GITHUB_REPO}/releases/latest"

if [[ -z "${TAG}" ]]; then
  RAW=$(curl -fsL "${API_URL}") || die "cannot fetch release info"
  TAG=$(printf '%s' "$RAW" | grep -m1 '"tag_name"' | sed -E 's/.*"tag_name": "([^"]*)".*/\1/')
  [[ -z "${TAG}" ]] && die "cannot determine latest tag"
  note "Latest tag ${TAG}"
else
  note "Using tag ${TAG}"
fi

TARBALL_URL="https://github.com/${GITHUB_REPO}/archive/refs/tags/${TAG}.tar.gz"
if [[ -n "${DOWNLOAD_DIR}" ]]; then
  mkdir -p "${DOWNLOAD_DIR}"
  TMPDIR="${DOWNLOAD_DIR%/}"
else
  TMPDIR="$(pwd)"
fi
ARCHIVE="${TMPDIR}/repo-${TAG}.tar.gz"

trap cleanup EXIT

info "Downloading ${TAG}"
curl -sSL --fail -o "${ARCHIVE}" "${TARBALL_URL}" || die "download failed"

info "Extracting"
tar -xzf "${ARCHIVE}" -C "${TMPDIR}" || die "extract failed"

EXTRACTED_DIR=$(find "${TMPDIR}" -mindepth 1 -maxdepth 1 -type d | grep -F "DuoKLI-")
[[ -d "${EXTRACTED_DIR}" ]] || die "extracted directory not found"

info "Installing to ${LOCATION}"
[[ -e "${LOCATION}" ]] && sudo rm -rf "${LOCATION}"

sudo mkdir -p "$(dirname "${LOCATION}")"
sudo mv "${EXTRACTED_DIR}" "${LOCATION}" || die "failed to move files into ${LOCATION}"

info "Setting up venv"
sudo "${LOCATION}"/bin/true 2>/dev/null || true
sudo chown -R "$(whoami)" "${LOCATION}"
python3 -m venv "${LOCATION}/venv" || die "venv creation failed"
"${LOCATION}/venv/bin/pip" install -q -U pip setuptools wheel

if [[ -f "${LOCATION}/requirements.txt" ]]; then
  info "Installing dependencies"
  "${LOCATION}/venv/bin/pip" install -q -r "${LOCATION}/requirements.txt"
else
  note "No requirements.txt"
fi

info "Creating wrapper ${BIN_PATH}"
WRAPPER_CONTENT=$(cat <<EOF
#!/usr/bin/env bash
cd "${LOCATION}"
exec "${LOCATION}/venv/bin/python" "${LOCATION}/DuoKLI.py" "\$@"
EOF
)
echo "${WRAPPER_CONTENT}" | sudo tee "${BIN_PATH}" >/dev/null
sudo chmod +x "${BIN_PATH}"

info "Done"
note "Launch with: duokli"
note "Wrapper at ${BIN_PATH}"
note "DuoKLI at ${LOCATION}"
exit 0
