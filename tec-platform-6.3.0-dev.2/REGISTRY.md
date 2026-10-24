# TEC client, USB and case register · 6.3.0-dev.2

Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
Author & Credits: https://www.alawise.es/1-s

## Technician workflow

1. Sign in to TEC with an active, confirmed technician account. Open **Client,
   USB & case dashboard** from Account, or `cases.php`, and verify TOTP.
2. Add a client, or use **Import clients from my confirmed requests**. Importing
   is repeatable and uses only requests assigned to the signed-in technician.
3. Before a visit, register the persistent ext4 filesystem UUID and assign the
   USB to that client. It is the UUID used by `aux.usb=`, not the label, device
   path, ESP UUID or a client's IP address. The portable image manifest records it.
4. Alternatively, accept a normal W request in `cli.php`. After local AUTORIZO,
   a persistent client sends its USB UUID and hashed DMI computer identity.
   The dashboard discovers the USB; assign its client in the USB register.
   Assign the first case separately if it arrived before the USB had a client.
5. A later approval using the same USB inherits its current client. Each approval
   creates a new case; a reboot within the existing authorization keeps the same
   case. Moving the USB to a different computer still requires new local consent.
6. Open a case to write notes, set Open / In progress / Waiting / Resolved, choose
   a follow-up date, inspect connection events or open its terminal. Dates use UTC.
   Use the **Follow-up due** filter for today's and overdue unresolved work.
7. **Close SSH authorization** revokes the gateway case and its resumed access.
   The client, USB, work item and history remain. Resolving a work item changes
   its work status; the authorization has its own explicit close control.

Each technician has a private register keyed by their approved account, available
from other browsers after sign-in and TOTP. An unrelated technician cannot browse,
link or edit its clients, USBs, cases, notes or events. This revision does not add
team sharing or cross-account terminal handoff.

## Live connection watch

The page checks every five seconds without replacing work-note drafts. A newly
discovered case appears in Connection watch and links to its details. Forms and a
manual Refresh button also work without JavaScript. Reload a case's history to
load its latest timeline entries.

- Gateway connected: the approved client WSS channel is available.
- Web terminal open: the gateway has an active browser terminal transport.
- Waiting for client / reboot: the authorization is retained but its client
  transport disconnected. No claim is made about why it disconnected.
- Status unknown: the gateway cannot be checked, the account/TOTP lease expired,
  or the last status is more than 30 seconds old.
- Authorization closed / expired: the permission ended; historical records stay.

Gateway availability does not prove an independent direct SSH socket is in use.
The client IP is deliberately not used as its durable identity. Work notes are
explicit entries; terminal keystrokes, screen output and commands are not recorded.

## Standalone C / offline SSH

Use **Record C / offline work**, choose the client and USB, and keep notes and
follow-up dates in that case. Its status is **manual tracking** because standalone
C has no active channel to the gateway. Its revocation remains on the client.
The direct SSH route approved as part of a W case shares that case's deadline;
the dashboard monitors the W channel, not independent direct SSH connections.

## Identity and inventory

The persistent filesystem UUID identifies the USB profile; the hashed DMI UUID
distinguishes computers used with it. These are inventory labels, not credentials
or hardware attestation. Cloned USB images need different filesystem/profile
UUIDs before issuing them as separate assets. Reusing a UUID merges their label.

USB client reassignment applies to future cases. Existing cases keep their
historical client unless edited explicitly. Marking a USB Lost / Retired records
inventory status; use Close SSH authorization on any active case to end access.

## Upgrade and storage

Install both the TEC and CLI updates. The suite installer now copies `history.py`
alongside `/opt/aux-cli/server.py`. A manual gateway update must copy both files
before restarting `aux-cli`. No new Python dependency or SQL server is required;
the gateway uses the standard-library SQLite module.

- TEC business records: `/var/lib/aux-assist/registry.json`, private mode 0600,
  serialized by `.registry.lock` and replaced atomically as one document.
- Gateway event journal: `/var/lib/aux-cli/history.sqlite3`, private mode 0600,
  SQLite WAL / FULL synchronous. Restarting the gateway retains it.
- Live reconnect capabilities: `/var/lib/aux-cli/cases/`, unchanged in purpose;
  closing authorization removes the capability file while retaining the journal.

Private runtime data is outside the webroot and source archives. The history API
requires a fresh signed control ticket and filters by its technician subject.
Claim events precede consent and contain no device labels. After consent, device
labels, event times, states and reasons are journaled;
client bearer tokens, private SSH keys and API keys are excluded from business
records and events. The reconnect capability store keeps its existing private
key material separately.

The registry file has a 64 MiB read guard. Plan archival or a database migration
before reaching it; this initial register is intended for a small deployment.
Back up the entire private TEC directory and gateway state consistently during a
maintenance window with both services stopped; keep backups private. Restoring
the registry and journal from inconsistent dates can leave event cursors ahead
of the restored journal. Preserve the two together.

Older cases first enter the journal on reconnect or a new recorded transition;
past unrecorded history cannot be reconstructed. An older Live/USB agent can still
connect, but device labels arrive only from the updated agent. Rebuild the Live
or portable overlay from this source revision for automatic USB linking. The
generic clean/PXE profile supplies no persistent USB identity.

## Validation in this revision

The registry PHP fixtures test ownership, duplicate prevention, replay safety,
notes, valid dates, USB reassignment, retained history and honest offline states.
The real PHP page is tested against a TLS gateway with isolated account sessions:
authenticated sync, TOTP/CSRF gates, escaped content, cross-technician denial,
remote revocation and retained notes. Gateway tests cover journal restart,
pagination, secret exclusion, fixed device identity and revocation with an
unwritable journal. A journal failure is also reported by health/history endpoints;
TEC treats an uncheckable gateway as unknown. Node DOM fixtures cover live refresh, drafts, safe text,
dashboard terminal links and reconnect behavior.

These are local development tests. The public server has not been updated, and
this source revision has not been built into or booted as a Fedora Live image.
