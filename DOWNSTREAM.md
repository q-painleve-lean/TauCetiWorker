# q-painleve-lean downstream branch

`downstream` is upstream `TauCetiProject/TauCetiWorker` `main` plus the changes below, used by the
`q-painleve-lean/QPainleve` workers (`~/.config/qpainleve/workers.toml`). `main` of this fork mirrors
upstream and carries nothing of its own.

Each change is one commit with a test. Remove a change once upstream carries the same behaviour.

| Change | Why | Files | Remove when |
| --- | --- | --- | --- |
| Spend Codex credits above a floor once a window is spent | The pacer reads only the plan's usage windows, so once a weekly window reaches 100% every Codex worker waits for its reset even with credits left (it waited two days with 59,005 credits). With `TAUCETI_CODEX_CREDIT_FLOOR` set (QPainleve: 20000 in each worker's `env`), a spent window the credits extend reads as over pace: `ignore_quota` workers run, paced workers still wait, and spending stops at the floor or when the overage limit is reached. Unset, behaviour is upstream's | `tauceti_worker/codex_credits.py`, `tauceti_worker/quota.py` (`_codex_from_payload`), `tests/quota_codex_credits.py`, `tests/run-all` | upstream's pacer accounts for Codex credits |
| Use the q-painleve-lean TauCetiTools fork | The worker reads Tools' survey contract to decide which merge-queue recovery requests to act on. Upstream's contract trusts only Tau Ceti's automation, so the QPainleve sweep's requests (posted as `qpainleve-automation[bot]`) were ignored. The fork's `downstream` adds trusted logins from `TAUCETI_REBASE_AUTHORS` (QPainleve: `qpainleve-automation[bot]` in each worker's `env`). `[tool.uv] override-dependencies` resolves every `tauceti-tools` requirement, including `tauceti-review`'s, to the fork | `pyproject.toml` | the upstream Tools contract lets a downstream name its own sweep App |

## Running

The QPainleve fleet runs from this checkout's own environment (`uv sync --frozen`), with its own
runtime and state directories, so other fleets on the same login (each with its own checkout and
`workers.toml`) are unaffected by it. `~/.local/bin/tauceti-qpainleve` sets:

| Variable | Value |
| --- | --- |
| `TAUCETI_RUNTIME_DIR` | `$XDG_RUNTIME_DIR/tauceti-qpainleve` |
| `TAUCETI_WORKERS_STATE_DIR` | `~/.local/state/tauceti-qpainleve/workers` |

and runs `tauceti workers --config ~/.config/qpainleve/workers.toml` from this checkout's `.venv`.

## Taking a new upstream

Merge often; each change above is small so that merges stay clean.

```sh
git fetch upstream main
git push origin upstream/main:main   # keep main a mirror of upstream
git switch downstream
git merge upstream/main              # never rebase or force-push downstream
tests/run-all -j 12
git push origin downstream
uv sync --frozen
```

Then deploy as upstream's [rolling deploys](docs/workers.md#restarts-and-rolling-deploys) describe:
restart the manager with `tauceti-qpainleve workers manager-stop --leave-workers` and
`tauceti-qpainleve workers apply`, then `tauceti-qpainleve workers restart ID` for each worker.

On a conflict in a listed file, take upstream's version and reapply that change. Check each
"Remove when" condition after the merge and drop changes upstream now covers.
