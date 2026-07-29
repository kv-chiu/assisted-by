#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

repo_path="${REPO:-linux-full.git}"
lore_external="${LORE_EXTERNAL:-https://lore.kernel.org/all/}"
task_tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/assisted-by-refresh.XXXXXX")"

cleanup() {
  rm -rf -- "$task_tmp_dir"
  if command -v lei >/dev/null 2>&1; then
    lei daemon-kill >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

for required_command in git lei python3 tar; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    echo "error: required command not found: $required_command" >&2
    exit 127
  fi
done

# 1. fast-forward the kernel clone
if [ ! -e "$repo_path" ]; then
  git clone --bare --shallow-since="2026-01-01" --no-tags --single-branch \
    https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git "$repo_path"
else
  if [ "$(git --git-dir="$repo_path" rev-parse --is-bare-repository)" != "true" ]; then
    echo "error: $repo_path exists but is not a bare Git repository" >&2
    exit 1
  fi
  git --git-dir="$repo_path" fetch --no-tags origin \
    +refs/heads/master:refs/heads/master
fi

# 2. register lore and pull a complete, fresh submitted set
if ! lei ls-external | grep -Fqx "$lore_external"; then
  lei add-external "$lore_external"
fi
if ! lei ls-external | grep -Fqx "$lore_external"; then
  echo "error: lei external was not registered: $lore_external" >&2
  exit 1
fi
lei q -d mid -o - -f mboxrd \
  'b:"Assisted-by:" AND d:20260101..' > "$task_tmp_dir/lei.mbox"

# 3. parse into temporary outputs so a partial refresh cannot replace good data
python3 parse_commits.py "$repo_path" "$task_tmp_dir/data.json"
python3 parse_lei.py "$task_tmp_dir/lei.mbox" "$task_tmp_dir/lore_data.json"

# 4. compute kernel-wide line totals
python3 kernel_stats.py "$repo_path" "$task_tmp_dir/kernel_stats.json"

# 5. reject empty or regressing remote results before replacing published data
python3 validate_refresh.py \
  data.json lore_data.json \
  "$task_tmp_dir/data.json" "$task_tmp_dir/lore_data.json"
mv "$task_tmp_dir/data.json" data.json
mv "$task_tmp_dir/lore_data.json" lore_data.json
mv "$task_tmp_dir/kernel_stats.json" kernel_stats.json

# 6. assemble the web payload and inline it into index.html
python3 build_data.py

echo "refresh complete: $(date -u +%FT%TZ)"
