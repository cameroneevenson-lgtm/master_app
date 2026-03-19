# Master App

`master_app` is the first scaffold for a unified fabrication shell that sits above:

- `fabrication_flow_dashboard`
- `truck_nest_explorer`
- `inventor_to_radan`
- `radan_kitter`

This first version focuses on:

- a single PySide6 shell with navigation
- shared path/settings management
- truck + kit discovery from release/fabrication roots
- dashboard read-only visibility from `fabrication_flow.db`
- adapter-style actions for launching sibling tools
- a first-pass "run Inventor and copy outputs" workflow

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

## Pages

- `Home`
  - overall counts and quick launches
- `Truck Workspace`
  - truck and kit visibility across L/W roots
  - scaffold creation
  - Inventor handoff
  - RADAN Kitter launch
- `Dashboard`
  - read-only truck and kit visibility from `fabrication_flow.db`
- `Admin`
  - paths, launchers, kit mappings, and template settings

## Notes

- This scaffold intentionally uses adapter boundaries instead of importing sibling app modules directly.
- The sibling apps currently use overlapping top-level module names like `models.py` and `main_window.py`, so direct in-process imports would be brittle until those apps are packaged more cleanly.
- The master app therefore starts by reading shared files/databases and launching sibling tools through subprocess adapters.

