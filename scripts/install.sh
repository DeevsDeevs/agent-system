#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Install skills for Codex and/or Claude Code.

Usage:
  install.sh [--platform codex|claude|both]
             [--repo URL] [--clone-dir PATH] [--repo-dir PATH] [--repo-ref REF]
             [--target PATH] [--mode symlink|copy]
             [--skills comma,separated,list]
             [--non-interactive]
             [--uninstall]

Defaults:
  --platform  codex
  --repo      https://github.com/DeevsDeevs/agent-system.git
  --clone-dir ~/src/agent-system
  --target    ${AGENTS_HOME:-~/.agents}/skills
  --mode      symlink

Examples:
  install.sh --platform codex --target ~/.agents/skills
  install.sh --platform claude
  install.sh --platform both --skills chain-system,dev-experts
  install.sh --platform codex --repo-ref v1.2.0
  install.sh --platform codex --uninstall --skills chain-system
  install.sh --non-interactive --platform codex --target ~/.agents/skills
USAGE
}

PLATFORM="codex"
REPO_URL="https://github.com/DeevsDeevs/agent-system.git"
CLONE_DIR="$HOME/src/agent-system"
TARGET=""
MODE="symlink"
SKILLS_CSV=""
SKILLS_LIST=()
REPO_DIR=""
REPO_REF=""
UNINSTALL="false"
NON_INTERACTIVE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      PLATFORM="$2"; shift 2; ;;
    --repo)
      REPO_URL="$2"; shift 2; ;;
    --clone-dir)
      CLONE_DIR="$2"; shift 2; ;;
    --repo-dir)
      REPO_DIR="$2"; shift 2; ;;
    --repo-ref)
      REPO_REF="$2"; shift 2; ;;
    --target)
      TARGET="$2"; shift 2; ;;
    --mode)
      MODE="$2"; shift 2; ;;
    --skills)
      SKILLS_CSV="$2"; shift 2; ;;
    --non-interactive)
      NON_INTERACTIVE="true"; shift 1; ;;
    --uninstall)
      UNINSTALL="true"; shift 1; ;;
    -h|--help)
      usage; exit 0; ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

prompt() {
  local __var="$1"
  local __label="$2"
  local __default="$3"
  local __input=""
  if [[ -n "$__default" ]]; then
    if [[ -r /dev/tty ]]; then
      read -r -p "$__label [$__default]: " __input < /dev/tty
    else
      read -r -p "$__label [$__default]: " __input
    fi
    if [[ -z "$__input" ]]; then
      __input="$__default"
    fi
  else
    if [[ -r /dev/tty ]]; then
      read -r -p "$__label: " __input < /dev/tty
    else
      read -r -p "$__label: " __input
    fi
  fi
  printf -v "$__var" "%s" "$__input"
}

ask_yn() {
  local __var="$1"
  local __label="$2"
  local __default="$3"
  local __input=""
  if [[ -r /dev/tty ]]; then
    read -r -p "$__label [${__default}]: " __input < /dev/tty
  else
    read -r -p "$__label [${__default}]: " __input
  fi
  if [[ -z "$__input" ]]; then
    __input="$__default"
  fi
  printf -v "$__var" "%s" "$__input"
}

run_interactive() {
  echo "Interactive install"
  prompt PLATFORM "Platform (codex|claude|both)" "$PLATFORM"
  local action="install"
  if [[ "$UNINSTALL" == "true" ]]; then
    action="uninstall"
  fi
  prompt action "Action (install|uninstall)" "$action"
  if [[ "$action" == "uninstall" ]]; then
    UNINSTALL="true"
  else
    UNINSTALL="false"
  fi

  prompt SKILLS_CSV "Skills (comma-separated, blank = all)" "$SKILLS_CSV"
  if [[ "$PLATFORM" == "codex" || "$PLATFORM" == "both" ]]; then
    prompt TARGET "Codex skills target dir" "${TARGET:-${CODEX_HOME:-$HOME/.codex}/skills}"
  fi

  local advanced="n"
  ask_yn advanced "Show advanced options? (y/N)" "N"
  if [[ "$advanced" == "y" || "$advanced" == "Y" ]]; then
    prompt MODE "Mode (symlink|copy)" "$MODE"

    local repo_dir_input=""
    prompt repo_dir_input "Local repo dir (blank to clone)" "$REPO_DIR"
    if [[ -n "$repo_dir_input" ]]; then
      REPO_DIR="$repo_dir_input"
    else
      prompt REPO_URL "Repo URL" "$REPO_URL"
      prompt CLONE_DIR "Clone dir" "$CLONE_DIR"
    fi

    prompt REPO_REF "Repo ref (tag/branch/commit, optional)" "$REPO_REF"
  fi
}

if [[ "$NON_INTERACTIVE" == "false" ]]; then
  if [[ -r /dev/tty ]]; then
    run_interactive
  else
    NON_INTERACTIVE="true"
  fi
fi

ensure_repo() {
  if [[ -z "$REPO_DIR" ]]; then
    if [[ -d "$CLONE_DIR/.git" ]]; then
      REPO_DIR="$CLONE_DIR"
      git -C "$REPO_DIR" fetch --all --prune
    else
      git clone "$REPO_URL" "$CLONE_DIR"
      REPO_DIR="$CLONE_DIR"
    fi
  fi

  if [[ -n "$REPO_REF" ]]; then
    git -C "$REPO_DIR" checkout "$REPO_REF"
    git -C "$REPO_DIR" pull --ff-only 2>/dev/null || true
  fi
}

cleanup_repo() {
  if [[ -d "$CLONE_DIR/.git" ]]; then
    rm -rf "$CLONE_DIR"
    echo "Removed cloned repo: $CLONE_DIR"
  fi
}

fetch_nautilus_docs() {
  local docs_dir="$REPO_DIR/nautilus-docs/references/docs"

  if [[ -d "$docs_dir" ]]; then
    return
  fi

  echo "Fetching NautilusTrader docs..."
  local temp
  temp=$(mktemp -d)
  trap "rm -rf '$temp'" RETURN
  git clone --filter=blob:none --sparse --depth 1 \
    https://github.com/nautechsystems/nautilus_trader.git "$temp"
  git -C "$temp" sparse-checkout set docs/
  rm -rf "$temp/docs/api_reference"
  mkdir -p "$(dirname "$docs_dir")"
  mv "$temp/docs" "$docs_dir"
}

fetch_skill_deps() {
  for skill in "${SKILLS_LIST[@]}"; do
    if [[ "$(basename "$skill")" == "nautilus-docs" ]]; then
      fetch_nautilus_docs
    fi
  done
}

collect_skills() {
  SKILLS_LIST=()
  if [[ -n "$SKILLS_CSV" ]]; then
    IFS=',' read -r -a SKILLS_LIST <<< "$SKILLS_CSV"
  else
    while IFS= read -r -d '' skill_path; do
      local skill_dir rel
      skill_dir="$(dirname "$skill_path")"
      rel="${skill_dir#$REPO_DIR/}"
      SKILLS_LIST+=("$rel")
    done < <(find "$REPO_DIR" \
        -path "$REPO_DIR/.git" -prune -o \
        -path "$REPO_DIR/.codex" -prune -o \
        -path "$REPO_DIR/.agents" -prune -o \
        -path "$REPO_DIR/.tmp" -prune -o \
        -path "$REPO_DIR/.github" -prune -o \
        -name SKILL.md -print0)
  fi
}

install_codex() {
  ensure_repo
  collect_skills
  fetch_skill_deps

  TARGET="${TARGET:-${CODEX_HOME:-$HOME/.codex}/skills}"
  mkdir -p "$TARGET"

  for skill in "${SKILLS_LIST[@]}"; do
    local src dst
    src="$REPO_DIR/$skill"
    dst="$TARGET/$skill"
    if [[ "$MODE" == "symlink" ]]; then
      ln -sfn "$src" "$dst"
    elif [[ "$MODE" == "copy" ]]; then
      rm -rf "$dst"
      cp -a "$src" "$dst"
    else
      echo "Unknown mode: $MODE" >&2
      exit 1
    fi
    echo "Installed $skill -> $dst"
  done

  printf '\nDone. Restart Codex to reload skills.\n'
}

uninstall_from() {
  local target_dir="$1"

  if [[ ! -d "$target_dir" ]]; then
    echo "Nothing to uninstall — $target_dir does not exist."
    return
  fi

  local skills_to_remove=()
  if [[ -n "$SKILLS_CSV" ]]; then
    IFS=',' read -r -a skills_to_remove <<< "$SKILLS_CSV"
  else
    for entry in "$target_dir"/*/; do
      [[ -f "${entry}SKILL.md" ]] && skills_to_remove+=("$(basename "$entry")")
    done
  fi

  for skill_name in "${skills_to_remove[@]}"; do
    local dst="$target_dir/$skill_name"
    if [[ -L "$dst" ]]; then
      rm -f "$dst"
      echo "Removed $dst"
    elif [[ -d "$dst" && -f "$dst/SKILL.md" ]]; then
      rm -rf "$dst"
      echo "Removed $dst"
    else
      echo "Not found: $dst"
    fi
  done
}

uninstall_codex() {
  TARGET="${TARGET:-${CODEX_HOME:-$HOME/.codex}/skills}"
  uninstall_from "$TARGET"
  cleanup_repo
  printf '\nDone. Restart Codex to reload skills.\n'
}

install_claude() {
  ensure_repo
  collect_skills
  fetch_skill_deps

  local clone_abs marketplace
  clone_abs="$(cd "$REPO_DIR" && pwd)"
  marketplace="$(basename "$clone_abs")"

  clean_plugin_cache "$marketplace"

  printf 'Run inside Claude Code:\n\n'
  printf '  /plugin marketplace add %s\n\n' "$clone_abs"
  for skill in "${SKILLS_LIST[@]}"; do
    printf '  /plugin install %s@%s\n' "$(basename "$skill")" "$marketplace"
  done
  printf '\nDone. Restart Claude Code to reload skills.\n'
}

uninstall_claude() {
  local marketplace
  marketplace="$(basename "$CLONE_DIR")"
  clean_plugin_cache "$marketplace"
  cleanup_repo
  printf '\nDone. Remove any installed plugins inside Claude Code with:\n'
  printf '  /plugin marketplace remove %s\n' "$marketplace"
}

clean_plugin_cache() {
  local marketplace="$1"
  local plugins_dir="$HOME/.claude/plugins"
  if [[ -d "$plugins_dir/cache/$marketplace" || -d "$plugins_dir/marketplaces/$marketplace" ]]; then
    rm -rf "$plugins_dir/cache/$marketplace" "$plugins_dir/marketplaces/$marketplace"
    if command -v jq &>/dev/null; then
      [[ -f "$plugins_dir/installed_plugins.json" ]] && \
        jq ".plugins |= with_entries(select(.key | test(\"@${marketplace}\$\") | not))" \
          "$plugins_dir/installed_plugins.json" > "$plugins_dir/installed_plugins.json.tmp" && \
        mv "$plugins_dir/installed_plugins.json.tmp" "$plugins_dir/installed_plugins.json"
      [[ -f "$plugins_dir/known_marketplaces.json" ]] && \
        jq "del(.\"$marketplace\")" \
          "$plugins_dir/known_marketplaces.json" > "$plugins_dir/known_marketplaces.json.tmp" && \
        mv "$plugins_dir/known_marketplaces.json.tmp" "$plugins_dir/known_marketplaces.json"
    fi
    echo "Cleaned plugin cache for $marketplace"
  fi
}

case "$PLATFORM" in
  codex)
    if [[ "$UNINSTALL" == "true" ]]; then
      uninstall_codex
    else
      install_codex
    fi
    ;;
  claude)
    if [[ "$UNINSTALL" == "true" ]]; then
      uninstall_claude
    else
      install_claude
    fi
    ;;
  both)
    if [[ "$UNINSTALL" == "true" ]]; then
      uninstall_codex
      printf '\n'
      uninstall_claude
    else
      install_codex
      printf '\n'
      install_claude
    fi
    ;;
  *)
    echo "Unknown platform: $PLATFORM" >&2
    usage
    exit 1
    ;;
esac
