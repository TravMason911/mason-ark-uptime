# Mason Ark uptime

Every 10 minutes GitHub Actions checks each site in `checks.json` from outside
the VPS (3 tries, 20 s apart, before a check counts as down) plus TLS
certificate expiry (warns at 14 days). A failing check opens an issue labelled
`down` (GitHub emails the owner); the issue closes itself on recovery.

- Add a site: a line in `checks.json` (`expect` status, optional `contains`,
  `json_ok` or `json_field`).
- Run now: Actions, uptime, Run workflow.
- PaqLink's `/healthz` also turns red when its nightly housekeeping is stale,
  so a stopped cron is caught here too.
