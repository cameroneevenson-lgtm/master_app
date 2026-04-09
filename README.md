# Master App

`master_app` boots its own multi-page shell again.

The shell keeps `truck_nest_explorer` close at hand, but the landing view now starts from a broader operations pulse instead of dropping straight into the same explorer workflow.

The project still sits above:

- `fabrication_flow_dashboard`
- `truck_nest_explorer`
- `inventor_to_radan`
- `radan_kitter`

The active runtime now focuses on:

- a shell-level home view with fabrication pulse, risk summary, and truck status snapshot
- an explorer-style truck workspace for L/W visibility, scaffold creation, and handoff actions
- a read-only dashboard page that mirrors key fabrication states
- shared settings and launchers for the surrounding tools
- a local master-app hot reload launcher with in-app reload controls

## Run

### Option 1

```powershell
cd C:\Tools\master_app
.\master_app.bat
```

### Option 2

```powershell
cd C:\Tools\master_app
C:\Tools\.venv\Scripts\python.exe app.py
```

### Option 3: hot reload during development

```powershell
cd C:\Tools\master_app
.\dev_run.bat
```

This keeps the same safe restart pattern as the explorer flow:

- watches Python files in both `master_app` and `truck_nest_explorer`
- shows an in-app reload banner
- auto-reloads after the timeout unless you click `Cancel Reload`

## Active UI

- `Home`
  - released / unreleased / blocked / complete counts
  - published fabrication pulse with truck-level risk summary
- `Truck Workspace`
  - truck and kit visibility across L/W roots
  - scaffold creation
  - Inventor handoff
  - RADAN Kitter launch
- `Dashboard`
  - read-only fabrication state with release / stage / blocker visibility
- `Admin`
  - shared roots, launchers, kit mappings, and diagnostics

## Notes

- The master shell still links out to `truck_nest_explorer`, but it no longer boots the explorer as the primary window.
- Hot reload handshake files for the master entrypoint live under `master_app\_runtime`.
- The Git-backed working repo lives directly in `C:\Tools\master_app`.
