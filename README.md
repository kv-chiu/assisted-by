# Assisted-by

Tracks the `Assisted-by:` tag in Linux mainline since 2026-01-01: which AI models and tools
have shown up in disclosed kernel commits, what they have actually merged, and how that
compares to what is being submitted on lkml.

Live page: https://assisted-by.dev

## Why this exists

In early 2026 the Linux kernel adopted a policy for AI-assisted contributions: allowed,
but they must carry an `Assisted-by:` tag naming the model. This page is a single static
view of what that tag has produced so far. No auth, no analytics, no JS frameworks. Open
the page, the data is already inlined.

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

## Files

```
index.html         single-file site, JSON inlined
og.png / .svg      Open Graph card (1200x630)
favicon.*          icons
parse_commits.py   merged-side parser (git log)
parse_lei.py       submitted-side parser (lei mboxrd)
kernel_stats.py    kernel-wide insertion / deletion / loc totals
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
5. `build_data.py` inlines the combined JSON into `index.html`.

The refresh writes parser output to a temporary directory and validates that counts and
the latest lore date do not regress before replacing published JSON. For an intentional
historical reclassification that reduces a count, run once with
`ALLOW_DATA_REGRESSION=1` and review the diff before publishing.

The GitHub Actions workflow runs daily and can also be started with `workflow_dispatch`.
It runs the standard-library test suite first, rotates the lei and kernel caches weekly,
and commits data only after JSON and whitespace validation succeed.

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
- Share of kernel-wide lines. GitHub's stats API refuses repos over 10k commits and
  computing diffstats from the partial clone would take hours.

## About this analysis

Built with assistance from Anthropic's Claude (Opus 4.7, via Claude Code) by a human
collaborator. Tag string normalisation choices in `parse_commits.py` are judgement calls;
the parser source is the authoritative answer for any "why was X bucketed as Y?" question.
The page deliberately avoids inferring motivation from tag content.

## License

MIT.
