# Assisted-by: Linux AI disclosure tracker

An interactive, static dashboard for the Linux kernel's `Assisted-by:` disclosures since
2026-01-01. It tracks which AI models, vendors, and tools appear in submitted patches and
merged mainline commits, how adoption changes over time, and which authors are behind the
merged work.

- **Live dashboard:** https://kv-chiu.github.io/assisted-by/
- **Repository:** https://github.com/kv-chiu/assisted-by
- **Forked from:** https://github.com/snek-git/assisted-by

## Why this exists

In early 2026 the Linux kernel adopted a policy for AI-assisted contributions: allowed,
but they must carry an `Assisted-by:` tag naming the model. This project turns those public
disclosures into a static, interactive dashboard. No auth, no analytics, no JavaScript
frameworks: open the page and the main dataset is already inlined.

## What the dashboard includes

- Cumulative merged-commit and line totals placed in the context of overall mainline activity.
- Rolling 7, 30, 45, 60, 90, and 180-day windows plus a cumulative `ALL` view.
- Submitted and merged breakdowns by model, vendor, and invocation tool.
- Daily activity charts and direct links to recent mainline commits.
- Optional author-concentration analysis with contributor-weighted model adoption, effective
  contributor counts, Top 1/Top 5 shares, and Gini coefficient.
- A dedicated **Authors** tab ranking every merged-commit author from highest to lowest; select
  an author to browse all of their disclosed-AI commits on kernel.org.

## Numbers come from two sources

**Merged side.** A shallow clone of `torvalds/linux` since 2026-01-01, then
`git log --grep="Assisted-by:" -i --shortstat`. Each commit and each tag line is counted
directly. Lines added and removed come from `--shortstat`.

**Submitted side.** [`lei`](https://public-inbox.org/INSTALL.html) querying
[lore.kernel.org/all](https://lore.kernel.org/all):

```
lei q -d mid -f mboxrd 'b:"Assisted-by:" AND d:20260101..'
```

The mbox is then deduplicated by `(canonical subject, sender)` so that v1/v2/v3 respins
collapse, replies (`Re:`) drop, cover letters (`[PATCH 0/N]`) drop, and bot accounts
(Patchwork, kernel test robot, syzbot, 0day) drop. The `Assisted-by:` line must appear in
non-quoted body text.

## Tag classification

Every tag string is parsed into `{vendor, model, tool}`:

- **vendor** is the lab that trained the model (Anthropic, OpenAI, Google, DeepSeek, Z.ai).
- **model** is the canonical model name (Opus 4.6, GPT-5.4, Gemini 3.1 Pro, deepseek-v3.2).
- **tool** is how it was invoked (Direct / API, Claude Code, Cursor, GitHub Copilot, OpenCode, ...).

Wrappers attribute to the underlying model. So `GitHub Copilot:claude-sonnet-4.6` counts
as Anthropic Sonnet 4.6 under the Copilot tool. Multi-tag commits (e.g. Claude + Codex on
the SMB security fix) attribute lines to each disclosed model. That means bucket sums can
exceed the global total by design.

## Time windows

The page offers rolling 7, 30, 45, 60, 90, and 180-day views plus `ALL`, with 45 days as
the default. Windows are anchored to the latest date present in the dataset rather than the
viewer's clock. Each finite window is compared with the immediately preceding equal-length
window using percentage-point changes.

Daily dimension counters count a vendor, model, or tool at most once per patch. A patch can
still disclose more than one vendor or tool, so combined penetration percentages can exceed
100%. `ALL` is explicitly historical cumulative data rather than a statement about current
adoption.

## Author analysis

Author-adjusted analysis is off by default. Enabling it replaces the model ranking with a
contributor-weighted view and reveals author count, effective contributor count, Top 1 and
Top 5 patch shares, and the Gini coefficient for the selected window. Each sender counts at
most once per model in the contributor-weighted share, whether they submitted one patch or
five hundred.

For each model, effective contributors are the inverse Simpson concentration
`1 / sum(s_i^2)`, where `s_i` is one author's share of that model's patches. The view also
recalculates model penetration after removing the most prolific one and five authors across
the window. This makes it possible to distinguish broad adoption from a high-volume author.

Contributor identities are stable SHA-256-derived IDs of normalized sender addresses. Raw
names and addresses are not included in the browser's window aggregates. One address is one
identity; aliases belonging to the same person are not currently merged.

The separate **Authors** tab uses public author names from merged mainline commits. It is not
part of the anonymous submitted-patch concentration analysis: its purpose is to make the
commit counts auditable through direct kernel.org links.

## Files

```
index.html         static page with the default analytics JSON inlined
author_data.json   anonymous author-dominance summaries, loaded only on demand
og.png / .svg      Open Graph card (1200x630)
favicon.*          icons
parse_commits.py   merged-side parser (git log)
parse_lei.py       submitted-side parser (lei mboxrd)
kernel_stats.py    kernel-wide insertion / deletion / loc totals
window_stats.py    fixed rolling-window and prior-window aggregates
build_data.py      combines all three intermediates and inlines the JSON into index.html
refresh.sh         end-to-end refresh: fetch, parse, build
data.json          merged parser output
lore_data.json     submitted parser output
kernel_stats.json  kernel-wide totals
```

## Refreshing the data

Install the required commands first. On Ubuntu 24.04, `lei` is a separate binary package;
installing the `public-inbox` server package does not provide it:

```
sudo apt-get install lei git python3
```

```
./refresh.sh
```

Does, in order:

1. `git fetch --shallow-since=2026-01-01` on `linux-full.git`.
2. `lei q ... 'b:"Assisted-by:" AND d:20260101..'` to a fresh mbox.
3. Run `parse_commits.py` and `parse_lei.py`.
4. `kernel_stats.py` updates the kernel-wide denominator. With a restored kernel
   cache it processes only commits since the cached HEAD; a cache miss performs a
   complete recount.
5. `build_data.py` inlines the default JSON into `index.html` and writes the optional,
   lazy-loaded `author_data.json` summaries.

The refresh writes parser output to a temporary directory and validates that counts and
the latest lore date do not regress before replacing published JSON. For an intentional
historical reclassification that reduces a count, run once with
`ALLOW_DATA_REGRESSION=1` and review the diff before publishing.

The GitHub Actions workflow runs daily at 08:00 UTC+8 (00:00 UTC) and can also be started
with `workflow_dispatch`. It runs the standard-library test suite first, rotates the lei
and kernel caches weekly, and commits data only after JSON and whitespace validation succeed.

Run the local test suite with:

```
python3 -m unittest discover -s tests -v
```

Bootstrapping a fresh clone of this repo:

```
git clone --bare --shallow-since="2026-01-01" --no-tags --single-branch \
  https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git linux-full.git
lei add-external https://lore.kernel.org/all/
./refresh.sh
```

## What this page does not show

- Merge rate. Different humans use different tools for different patch types; the ratio
  is not a model quality signal.
- Submitted-versus-merged percentages. Same reason.
- Authorial intent or motivation behind any tag string.
- Patches that landed without disclosure. This page measures policy compliance, not
  actual AI usage in the kernel.
- Undisclosed AI assistance. This is a verifiable floor, not a census of all AI use.

## About this analysis

Originally built with assistance from Anthropic's Claude (Opus 4.7, via Claude Code) and
continued in this fork with OpenAI Codex. Tag string normalisation choices in
`parse_commits.py` are judgement calls; the parser source is the authoritative answer for
any "why was X bucketed as Y?" question. The page deliberately avoids inferring motivation
from tag content.

## License

MIT.
