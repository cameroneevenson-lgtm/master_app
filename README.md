# Master App

`master_app` now boots the same Truck Nest Explorer window from the master entrypoint, so the master app only shows the explorer workflow instead of the older multi-page shell.

The older shell files are still in the repo for reference, but they are no longer the active UI.

The project still sits above:

- `fabrication_flow_dashboard`
- `truck_nest_explorer`
- `inventor_to_radan`
- `radan_kitter`

The active runtime now focuses on:

- the exact `truck_nest_explorer` view and workflow
- the explorer's settings, actions, and truck/kit detail screens
- a local master-app hot reload launcher with the same in-app reload banner behavior

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

This mirrors the explorer hot reload flow:

- watches Python files in both `master_app` and `truck_nest_explorer`
- shows the in-app reload banner
- auto-reloads after the timeout unless you click `Cancel Reload`

## Active UI

- `Truck Nest Explorer`
  - truck and kit visibility across L/W roots
  - scaffold creation
  - Inventor handoff
  - RADAN Kitter launch
  - the same hot reload banner behavior when started through `dev_run.bat`

## Notes

- The master bootstrap now loads the explorer window first on `sys.path` so the explorer's own `models.py`, `services.py`, and `settings_store.py` win over the older shell modules.
- Hot reload handshake files for the master entrypoint live under `master_app\_runtime`.
- The Git-backed working repo lives directly in `C:\Tools\master_app`.
