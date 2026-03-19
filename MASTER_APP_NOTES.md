# Master App Notes

## Current apps

- `fabrication_flow_dashboard`
  - Operational scheduling and fabrication-state tracking.
  - Owns truck/kit state in `fabrication_flow.db`.
  - Syncs truck intake from `truck_registry.csv`.
- `inventor_to_radan`
  - BOM-to-Radan conversion tool.
  - Mostly a task-oriented utility, not a long-lived workspace.
- `radan_kitter`
  - Deep production tool for `.rpd` kit assignment and packet generation.
  - Large, mature standalone app.
- `truck_nest_explorer`
  - Filesystem/workflow hub for L/W folder discovery, scaffold creation, nest-summary preview, Inventor handoff, and kitter launching.
  - Still under active development.

## Recommendation

Build a new master shell above the four apps instead of doing a direct monolith merge right away.

Why:

- All four apps are already Python/PySide desktop tools, so a unified shell is realistic.
- `truck_nest_explorer` already orchestrates the workflow, but it is still moving. That makes it a strong feature module, but a risky sole foundation.
- `fabrication_flow_dashboard` already has the cleanest structured truck/kit data model, so it is the best candidate for the long-term operational source of truth.
- `inventor_to_radan` feels more like a workflow action/service than a full section of the future app.

## Best near-term shape

Create a fifth app, tentatively `fabrication_master`, with:

- a single `QApplication`
- a left navigation rail or top tabs
- shared truck selection / kit selection context
- adapters around the existing tools

Suggested sections:

- `Home`
  - Today's queue, attention items, shortcuts into truck work.
- `Truck Workspace`
  - Evolve from `truck_nest_explorer`.
  - Handles scaffold, W/L visibility, nest-summary preview, punch codes, and handoff actions.
- `Dashboard`
  - Fabrication schedule / stage board from `fabrication_flow_dashboard`.
- `Kitting`
  - Launch or later embed `radan_kitter`.
- `Rules / Admin`
  - Inventor rules, kit aliases, path config, templates, publish settings.

## What should be shared first

The first shared contract should be the truck/kit identity layer:

- truck number
- canonical kit name
- dashboard display name
- RADAN/project name
- fabrication-side relative path
- key artifact paths

This is the highest-value seam because the current apps already disagree slightly on kit naming:

- dashboard uses canonical names like `Body`, `Console`, `Interior`, `Exterior`
- explorer uses mappings like `BODY | PAINT PACK`

The master app should own a shared kit catalog/alias map instead of letting each app keep its own naming assumptions.

## Data strategy

Recommended data ownership:

- `fabrication_flow_dashboard` database becomes the long-term operational source of truth for truck + kit state.
- `truck_nest_explorer` continues to derive filesystem status from L/W roots.
- `inventor_to_radan` remains a task runner with rule/config files.
- `radan_kitter` remains a tool module with its own operational files until later refactor.

Near-term rule:

- Do not force `truck_nest_explorer` state into the dashboard database yet.
- Instead, build a read model in the master shell that joins:
  - dashboard truck/kit state
  - explorer filesystem state
  - artifact presence

## Integration strategy

### Phase 1: shell and launch integration

- New master shell window.
- Reuse existing apps mostly as they are.
- Import shared service logic from `truck_nest_explorer` where practical.
- Launch `radan_kitter` and `inventor_to_radan` through adapters first.
- Optionally embed dashboard earlier than the others because its data model is already structured.

### Phase 2: extract reusable pages

- Refactor each app's `QMainWindow` toward reusable `QWidget`/page content.
- Keep top-level launchers for standalone use.
- Move business logic out of UI classes where needed.

### Phase 3: shared settings and shared context

- Unify root-path configuration.
- Unify kit mappings/aliases.
- Unify selected truck/kit context so one selection can drive all pages.

### Phase 4: deeper convergence

- Replace external launches with in-process pages where stable.
- Fold common file/path helpers into a shared package.
- Consider whether `inventor_to_radan` should become a modal workflow panel rather than a separate app.

## Practical first build

If we start implementation soon, the first version should do only this:

1. Show a truck list and selected-kit context.
2. Reuse explorer service logic for L/W status and scaffold actions.
3. Surface dashboard status for the same truck.
4. Offer one-click actions:
   - run Inventor -> Radan
   - copy outputs to L
   - launch RADAN Kitter
   - open nest summary
   - open project folder

That gives real value without forcing a risky rewrite.

## Key caution

Do not start by trying to fully embed all four UIs in one pass.

The safer order is:

1. shared models and settings
2. orchestration shell
3. stable page extraction
4. only then deep UI unification

## Likely starting point

The master app should probably borrow most heavily from:

- `truck_nest_explorer` for workflow orchestration
- `fabrication_flow_dashboard` for canonical ops data

So the conceptual direction is:

`truck_nest_explorer` workflow brain + `fabrication_flow_dashboard` data spine + adapters for `inventor_to_radan` and `radan_kitter`
