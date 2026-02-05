#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Install Codex skills and/or print Claude Code plugin install commands.

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
  --target    ${CODEX_HOME:-~/.codex}/skills
  --mode      symlink

Examples:
  install.sh --platform codex --target ~/.codex/skills
  install.sh --platform claude
  install.sh --platform both --skills chain-system,dev-experts
  install.sh --platform codex --repo-ref v1.2.0
  install.sh --platform codex --uninstall --skills chain-system
  install.sh --non-interactive --platform codex --target ~/.codex/skills
USAGE
}

PLATFORM="codex"
REPO_URL="https://github.com/DeevsDeevs/agent-system.git"
CLONE_DIR="$HOME/src/agent-system"
TARGET="${CODEX_HOME:-$HOME/.codex}/skills"
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

  if [[ "$PLATFORM" == "codex" || "$PLATFORM" == "both" ]]; then
    prompt TARGET "Codex skills target dir" "$TARGET"
    prompt SKILLS_CSV "Skills (comma-separated, blank = all)" "$SKILLS_CSV"
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
    else
      git clone "$REPO_URL" "$CLONE_DIR"
      REPO_DIR="$CLONE_DIR"
    fi
  fi

  if [[ -n "$REPO_REF" ]]; then
    git -C "$REPO_DIR" fetch --tags --prune
    git -C "$REPO_DIR" checkout "$REPO_REF"
  fi
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
        -path "$REPO_DIR/.github" -prune -o \
        -name SKILL.md -print0)
  fi
}

install_codex() {
  ensure_repo

  mkdir -p "$TARGET"

  collect_skills
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

uninstall_codex() {
  if [[ -z "$SKILLS_CSV" ]]; then
    ensure_repo
  elif [[ -n "$REPO_REF" ]]; then
    echo "Warning: --repo-ref is ignored when --skills is provided for uninstall." >&2
  fi

  collect_skills
  for skill in "${SKILLS_LIST[@]}"; do
    local dst link_target
    dst="$TARGET/$skill"
    if [[ -L "$dst" ]]; then
      if [[ -n "$REPO_DIR" ]]; then
        link_target="$(readlink "$dst")"
        if [[ "$link_target" == "$REPO_DIR"* ]]; then
          rm -f "$dst"
          echo "Removed $dst"
        else
          echo "Skipping $dst (symlink not pointing to repo)" >&2
        fi
      else
        rm -f "$dst"
        echo "Removed $dst"
      fi
    elif [[ -d "$dst" ]]; then
      if [[ -f "$dst/SKILL.md" ]]; then
        rm -rf "$dst"
        echo "Removed $dst"
      else
        echo "Skipping $dst (no SKILL.md)" >&2
      fi
    else
      echo "Not found: $dst"
    fi
  done

  printf '\nDone. Restart Codex to reload skills.\n'
}

print_claude_instructions() {
  cat <<'EOC'
Run the following commands inside Claude Code:

/plugin marketplace add git@github.com:DeevsDeevs/agent-system.git
/plugin install chain-system@deevs-agent-system
/plugin install dev-experts@deevs-agent-system
/plugin install bug-hunters@deevs-agent-system
/plugin install research-experts@deevs-agent-system
/plugin install cost-status@deevs-agent-system
/plugin install arxiv-search@deevs-agent-system

Note: These are Claude Code commands and will not run in a shell.
EOC
}

print_claude_uninstall() {
  cat <<'EOC'
Run the following commands inside Claude Code:

/plugin uninstall chain-system@deevs-agent-system
/plugin uninstall dev-experts@deevs-agent-system
/plugin uninstall bug-hunters@deevs-agent-system
/plugin uninstall research-experts@deevs-agent-system
/plugin uninstall cost-status@deevs-agent-system
/plugin uninstall arxiv-search@deevs-agent-system

Note: These are Claude Code commands and will not run in a shell.
EOC
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
      print_claude_uninstall
    else
      print_claude_instructions
    fi
    ;;
  both)
    if [[ "$UNINSTALL" == "true" ]]; then
      uninstall_codex
      printf '\n'
      print_claude_uninstall
    else
      install_codex
      printf '\n'
      print_claude_instructions
    fi
    ;;
  *)
    echo "Unknown platform: $PLATFORM" >&2
    usage
    exit 1
    ;;
esac
