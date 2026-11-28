Done check on `ea2f11eb`, against `origin/main`, 28 November 2026 13:49, 2087 s, partial run (journeys,axe,order,tasks)

| Step | Result | Seconds | Notes | Log |
|---|---|---|---|---|
| Journeys (`journeys`) | PASS | 811 | 797 passed | `done-check-out2/logs/journeys.log` |
| Accessibility: axe, WCAG 2.2 AA (`axe`) | PASS (known on main) | 593 | known on main: 7 (7 items) | `done-check-out2/logs/axe.log` |
| Accessibility: reading and Tab order (`order`) | PASS | 259 | - | `done-check-out2/logs/order.log` |
| Accessibility: keyboard tasks (`tasks`) | PASS | 424 | 339 passed | `done-check-out2/logs/tasks.log` |

Pages checked for accessibility: every page.

Known on main (listed in tools/done-check-baseline.json; not caused by this change):
- axe: settings-general-backup.html, full backups with Checked and Restore|axe light|target-size
- axe: settings-general-backup.html, full backups with Checked and Restore|axe dark|target-size
- axe: settings-general-backup.html, full backups with Checked and Restore|axe high contrast|target-size
- axe: Restore a full backup, restoring|axe light|target-size
- axe: Restore a full backup, restored|axe light|target-size
- axe: Restore a full backup, restored|axe dark|target-size

DONE-CHECK PASSED (partial run: not enough to call the change done)
