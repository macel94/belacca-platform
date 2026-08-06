#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel)
cd "$root"

printf '%-28s %-12s %-42s %s\n' 'PATH' 'BRANCH' 'COMMIT' 'WORKTREE'
printf '%-28s %-12s %-42s %s\n' '----' '------' '------' '---------'

show_repo() {
  local path=$1
  local branch commit dirty
  branch=$(git -C "$path" branch --show-current)
  if git -C "$path" rev-parse --verify HEAD >/dev/null 2>&1; then
    commit=$(git -C "$path" log -1 --format='%h %s')
  else
    commit='(no commits yet)'
  fi
  if [ -n "$(git -C "$path" status --short)" ]; then
    dirty='modified/untracked'
  else
    dirty='clean'
  fi
  printf '%-28s %-12s %-42s %s\n' "$path" "${branch:-detached}" "$commit" "$dirty"
}

show_repo .
for path in cloudnativepong francesco-belacca-site belacca-status belacca-gitops; do
  if [ -f "$path/.git" ] || [ -d "$path/.git" ]; then
    show_repo "$path"
  else
    echo "missing submodule: $path" >&2
  fi
done

echo
git submodule status
