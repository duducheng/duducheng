# Refreshing this profile

`README.md` is generated. Run `python3 render.py` (Python standard library only),
or use **Actions → Refresh profile README → Run workflow**. GitHub Actions also
refreshes it every Monday at 06:23 UTC and after generator/config changes.

Sources:

- `bio_source` in `info.json`: the live website's `Web` biography, converted to Markdown without executing JavaScript.
- The four lists in `info.json`: curated ordering for existing projects. The GitHub API resolves transferred repositories to their canonical names on every run.
- The selection preserves the original research, educational and miscellaneous projects, with newer published work added. Preprints are omitted. New repositories are not automatically added; edit the lists in `info.json` to update the selection. Empty sections are omitted.
- `description_overrides`: source-verified descriptions for repositories with missing or outdated metadata. Remove an override when the repository description catches up.
- Stars and forks: live GitHub API counts, summed once per displayed repository.

No personal access token or paid service is needed in Actions: it uses the built-in
`GITHUB_TOKEN` with repository contents write permission. Local runs may set
`GITHUB_TOKEN` to avoid unauthenticated API limits. Network requests have timeouts
and bounded retries; the README is written only after every source succeeds.

Run `python3 -m unittest discover -s tests` to check transfer deduplication,
bio conversion and preservation of the README on a source failure.
GitHub may delay schedules or disable scheduled workflows in inactive public
repositories; the manual action and local command remain available.

The project list is collapsed by default using GitHub-supported `<details>` /
`<summary>` HTML. The summary shows aggregate stars, forks, the refresh date, and
GitHub Actions attribution; expanding it reveals Research, Educational and Misc.
