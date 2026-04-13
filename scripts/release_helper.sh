#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)

PROJECT_NAME="PyISIS"
REQUIRED_BRANCH="main"
PYTHON_ABI="cp312"
PLATFORM_TAG="linux-x86_64"
ISIS_RUNTIME_VERSION="9.0.0"
SOURCE_INIT_FILE="python/isis_pybind/__init__.py"
BUILD_INIT_FILE="build/python/isis_pybind/__init__.py"
BUILD_PACKAGE_DIR="build/python/isis_pybind"
RELEASE_NOTES_FILE="RELEASE.md"
MANUAL_RELEASE_DOC="doc_development_process/how_to_release_manually.md"
README_FILE="README.md"
DIST_DIR="dist"

log() {
  printf '[release-helper] %s\n' "$*"
}

warn() {
  printf '[release-helper] warning: %s\n' "$*" >&2
}

die() {
  printf '[release-helper] error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  scripts/release_helper.sh prepare <tag>
  scripts/release_helper.sh publish-tag <tag>

Commands:
  prepare      Validate release inputs and generate dist assets.
  publish-tag  Create and push an annotated git tag after prepare succeeds.

Arguments:
  <tag>        Must use the format vMAJOR.MINOR.PATCH, for example: v1.0.0
EOF
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

extract_python_version() {
  local file_path=$1
  local version

  [[ -f "$file_path" ]] || die "missing version file: $file_path"

  version=$(sed -nE 's/^__version__ = "([^"]+)"$/\1/p' "$file_path" | head -n 1)
  [[ -n "$version" ]] || die "failed to parse __version__ from $file_path"

  printf '%s\n' "$version"
}

require_repo_state() {
  cd "$REPO_ROOT"

  require_command git

  local branch_name
  branch_name=$(git rev-parse --abbrev-ref HEAD)
  [[ "$branch_name" == "$REQUIRED_BRANCH" ]] || die "current branch is '$branch_name'; switch to '$REQUIRED_BRANCH' before releasing"

  local worktree_status
  worktree_status=$(git status --short)
  [[ -z "$worktree_status" ]] || die "working tree is not clean; commit, stash, or clean changes before continuing"
}

parse_release_tag() {
  RELEASE_COMMAND=${1:-}
  RELEASE_TAG=${2:-}

  [[ -n "$RELEASE_COMMAND" ]] || {
    usage
    die "missing command"
  }

  [[ -n "$RELEASE_TAG" ]] || {
    usage
    die "missing release tag"
  }

  if [[ ! "$RELEASE_TAG" =~ ^v([0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
    die "invalid tag '$RELEASE_TAG'; expected format like v1.0.0"
  fi

  RELEASE_VERSION=${BASH_REMATCH[1]}
  PACKAGE_DIR_NAME="isis_pybind-${RELEASE_TAG}-${PLATFORM_TAG}-${PYTHON_ABI}-isis${ISIS_RUNTIME_VERSION}"
  ARCHIVE_NAME="${PACKAGE_DIR_NAME}.tar.gz"
  ARCHIVE_PATH="${DIST_DIR}/${ARCHIVE_NAME}"
  CHECKSUM_FILE="${DIST_DIR}/SHA256SUMS.txt"
}

check_version_consistency() {
  local source_version
  local build_version

  source_version=$(extract_python_version "$SOURCE_INIT_FILE")
  [[ "$source_version" == "$RELEASE_VERSION" ]] || die "$SOURCE_INIT_FILE has version '$source_version', expected '$RELEASE_VERSION'"

  [[ -d "$BUILD_PACKAGE_DIR" ]] || die "missing build package directory: $BUILD_PACKAGE_DIR; build the project before running prepare"

  build_version=$(extract_python_version "$BUILD_INIT_FILE")
  [[ "$build_version" == "$RELEASE_VERSION" ]] || die "$BUILD_INIT_FILE has version '$build_version', expected '$RELEASE_VERSION'"

  [[ -f "$RELEASE_NOTES_FILE" ]] || die "missing release notes file: $RELEASE_NOTES_FILE"
  grep -Fq "# PyISIS ${RELEASE_TAG}" "$RELEASE_NOTES_FILE" || die "$RELEASE_NOTES_FILE does not contain '# PyISIS ${RELEASE_TAG}'"

  local expected_asset_name
  expected_asset_name="$ARCHIVE_NAME"

  if ! grep -Fq "$expected_asset_name" "$README_FILE"; then
    warn "$README_FILE does not mention $expected_asset_name"
  fi

  if ! grep -Fq "$expected_asset_name" "$MANUAL_RELEASE_DOC"; then
    warn "$MANUAL_RELEASE_DOC does not mention $expected_asset_name"
  fi
}

locate_extension_module() {
  local matches=()

  shopt -s nullglob
  matches=("${BUILD_PACKAGE_DIR}"/_isis_core*.so)
  shopt -u nullglob

  [[ ${#matches[@]} -eq 1 ]] || die "expected exactly one _isis_core*.so under $BUILD_PACKAGE_DIR, found ${#matches[@]}"

  EXTENSION_MODULE_PATH=${matches[0]}
}

create_dist_assets() {
  locate_extension_module

  mkdir -p "$DIST_DIR"
  rm -rf "${DIST_DIR:?}/${PACKAGE_DIR_NAME}" "$ARCHIVE_PATH" "$CHECKSUM_FILE"

  mkdir -p "${DIST_DIR}/${PACKAGE_DIR_NAME}/isis_pybind"

  cp "$SOURCE_INIT_FILE" "${DIST_DIR}/${PACKAGE_DIR_NAME}/isis_pybind/__init__.py"
  cp "$EXTENSION_MODULE_PATH" "${DIST_DIR}/${PACKAGE_DIR_NAME}/isis_pybind/"
  cp "LICENSE" "${DIST_DIR}/${PACKAGE_DIR_NAME}/"

  tar czf "$ARCHIVE_PATH" -C "$DIST_DIR" "$PACKAGE_DIR_NAME"

  (
    cd "$DIST_DIR"
    sha256sum "$ARCHIVE_NAME" > "SHA256SUMS.txt"
  )

  log "created release archive: $ARCHIVE_PATH"
  log "created checksum file: $CHECKSUM_FILE"
}

ensure_prepare_outputs_exist() {
  [[ -f "$ARCHIVE_PATH" ]] || die "missing archive: $ARCHIVE_PATH; run prepare first"
  [[ -f "$CHECKSUM_FILE" ]] || die "missing checksum file: $CHECKSUM_FILE; run prepare first"
  grep -Fq "$ARCHIVE_NAME" "$CHECKSUM_FILE" || die "$CHECKSUM_FILE does not contain checksum entry for $ARCHIVE_NAME"
}

ensure_tag_absent() {
  if git rev-parse --verify --quiet "refs/tags/${RELEASE_TAG}" >/dev/null; then
    die "tag already exists locally: ${RELEASE_TAG}"
  fi

  if git ls-remote --tags origin "refs/tags/${RELEASE_TAG}" | grep -q .; then
    die "tag already exists on origin: ${RELEASE_TAG}"
  fi
}

run_prepare() {
  require_repo_state
  require_command sha256sum
  require_command tar

  check_version_consistency
  create_dist_assets

  log "prepare completed for ${RELEASE_TAG}"
  log "next step: scripts/release_helper.sh publish-tag ${RELEASE_TAG}"
}

run_publish_tag() {
  require_repo_state
  ensure_prepare_outputs_exist
  ensure_tag_absent

  git tag -a "$RELEASE_TAG" -m "${PROJECT_NAME} ${RELEASE_TAG}"
  git show --stat "$RELEASE_TAG"
  git push origin "$RELEASE_TAG"

  log "tag pushed: ${RELEASE_TAG}"
  log "next step: create a GitHub Release for ${RELEASE_TAG} and upload:"
  log "  - ${ARCHIVE_PATH}"
  log "  - ${CHECKSUM_FILE}"
}

main() {
  parse_release_tag "${1:-}" "${2:-}"

  case "$RELEASE_COMMAND" in
    prepare)
      run_prepare
      ;;
    publish-tag)
      run_publish_tag
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage
      die "unknown command: $RELEASE_COMMAND"
      ;;
  esac
}

main "$@"
