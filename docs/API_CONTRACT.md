# M2 Timetable API Contract

Version: `1.0`  
Base path: `/`  
Authentication: bearer JWT on all endpoints below. Examples show successful responses; IDs are illustrative. `provenance` is one of `REAL_DSATM_PDF`, `SYNTHETIC`, or `INFERRED`.

## Shared shapes

Timetable sessions use canonical A-Block room IDs only. `periods` is an ordered list of period numbers. A multi-period item has one `block_id`; parallel B1/B2 lab sessions have the same `block_id`, different `batch` values, and their own room assignments. Roomless activities have `room_id: null` and `room_required: false`. `raw_label` preserves the parsed source label.

```json
{
  "id": 501,
  "term_code": "2026-27-ODD",
  "section_code": "E",
  "batch": "ALL",
  "day": "Wed",
  "periods": [1, 2],
  "subject_code": "BCS502",
  "subject_name": "Machine Learning",
  "faculty_id": 31,
  "faculty_initials": "PP",
  "faculty_name": "Parvathisha Pudugosula",
  "room_id": "A-F2-02",
  "room_required": true,
  "raw_label": "5TH E SECTION; P1-P2 ML (PP)",
  "block_id": "2026-27-ODD-E-WED-P1-P2-1",
  "provenance": "REAL_DSATM_PDF",
  "version": 1
}
```

Conflict objects have `type` (`room`, `faculty`, or `section`), `term_code`, `day`, `period`, and the conflicting `session_ids`. Batch-parallel B1/B2 sessions in the same section and block are allowed when each batch has a distinct room.

## Endpoints

### `GET /sections`

Lists timetable sections. Optional filters: `term`.

Permission: any authenticated role.

```json
[
  {"term_code":"2026-27-ODD","code":"A","name":"5th A","division_code":"CSE-1","provenance":"REAL_DSATM_PDF"},
  {"term_code":"2026-27-ODD","code":"E","name":"5th E","division_code":"CSE-5","provenance":"REAL_DSATM_PDF"}
]
```

### `GET /sections/{section_code}/timetable`

Lists one section's sessions. Required query: `term`. Optional filters: `day`, `batch` (`ALL`, `B1`, or `B2`). Students may request only their mapped section; other authenticated roles may request any section.

```json
[{"id":501,"term_code":"2026-27-ODD","section_code":"E","batch":"ALL","day":"Wed","periods":[1,2],"subject_code":"BCS502","subject_name":"Machine Learning","faculty_id":31,"faculty_initials":"PP","faculty_name":"Parvathisha Pudugosula","room_id":"A-F2-02","room_required":true,"raw_label":"5TH E SECTION; P1-P2 ML (PP)","block_id":"2026-27-ODD-E-WED-P1-P2-1","provenance":"REAL_DSATM_PDF","version":1}]
```

### `GET /students/me`

Returns the authenticated student's own roster record and inferred division-to-section mapping. Student role only; other roles receive `403`.

```json
{"usn":"<redacted>","full_name":"<redacted>","division_code":"CSE-5","section_code":"E","lab_batch":"A1","provenance":"REAL_DSATM_PDF","mapping_data_status":"INFERRED"}
```

### `GET /timetable/student/me`

Returns the authenticated student's timetable. Student role only. Division maps to the term section; `A1` selects batch `B1`, `A2` selects batch `B2`, and `ALL` sessions apply to both batches.

```json
{"usn":"<redacted>","term_code":"2026-27-ODD","division_code":"CSE-5","section_code":"E","lab_batch":"A1","sessions":[{"id":501,"day":"Wed","periods":[1,2],"subject_code":"BCS502","subject_name":"Machine Learning","faculty_initials":"PP","room_id":"A-F2-02","batch":"ALL","room_required":true,"raw_label":"5TH E SECTION; P1-P2 ML (PP)","block_id":"2026-27-ODD-E-WED-P1-P2-1","provenance":"REAL_DSATM_PDF","version":1}]}
```

### `GET /timetable/faculty/{faculty_id}`

Lists sessions assigned to the term-scoped faculty record. Required query: `term`; optional `day`. Faculty and HOD may read their own timetable; admin may read any faculty timetable. Faculty IDs are term-scoped; initials are not merged across terms.

```json
{"faculty_id":31,"term_code":"2026-27-ODD","initials":"PP","name":"Parvathisha Pudugosala","sessions":[{"id":501,"section_code":"E","day":"Wed","periods":[1,2],"subject_code":"BCS502","room_id":"A-F2-02","provenance":"REAL_DSATM_PDF","version":1}]}
```

### `GET /rooms/{room_id}/timetable`

Lists sessions in a canonical A-Block room. Required query: `term`; optional `day`. `room_id` accepts canonical room IDs or resolver-supported labels. Any authenticated role may read room timetables.

```json
{"room_id":"A-F2-02","term_code":"2026-27-ODD","sessions":[{"id":501,"section_code":"E","day":"Wed","periods":[1,2],"subject_code":"BCS502","room_id":"A-F2-02","provenance":"REAL_DSATM_PDF","version":1}]}
```

### `GET /rooms/availability?day={day}&period={period}`

Lists A-Block rooms available for the requested weekday and period. Optional query: `term`; when omitted, the active term is used. Any authenticated role may read availability.

```json
{"day":"Wed","period":1,"term_code":"2026-27-ODD","rooms":[{"room_id":"A-F2-03","available":true,"provenance":"SYNTHETIC"},{"room_id":"A-F2-02","available":false,"session_ids":[501],"provenance":"SYNTHETIC"}]}
```

### `GET /timetable/conflicts`

Returns detected conflicts without changing sessions. Required query: `term`. Admin and HOD only.

```json
{"term_code":"2026-27-ODD","conflicts":[{"type":"room","day":"Tue","period":3,"session_ids":[501,502]}]}
```

### `POST /timetable/sessions`

Creates one session. Admin only. Request fields: `term_code`, `section_code`, `batch`, `day`, `periods`, `subject_code`, `faculty_id` (nullable), `room_id` (nullable canonical ID), `room_required`, `raw_label`, and `block_id` (nullable). `provenance` is `SYNTHETIC` for manually entered sessions. A clash returns `409` with the conflict object; the session is not written.

```json
{"term_code":"2026-27-ODD","section_code":"E","batch":"ALL","day":"Wed","periods":[7],"subject_code":"BCS503","faculty_id":31,"room_id":"A-F2-02","room_required":true,"raw_label":"Manual addition","block_id":null}
```

Response: the created session object from the shared shape, with a generated `id`, `version: 1`, and `provenance: "SYNTHETIC"`.

### `PATCH /timetable/sessions/{session_id}`

Updates an existing session. Admin only. The request contains one or more mutable session fields plus required `expected_version`. A clash returns `409` and leaves the session unchanged. A stale version returns `409` with `{"detail":"version conflict"}`. Successful updates increment `version` by one.

```json
{"room_id":"A-F2-03","expected_version":1}
```

Response: the updated session object from the shared shape.

### `GET /meta/data-status`

Returns imported dataset and provenance status. Any authenticated role may read it.

```json
{"terms":[{"code":"2026-27-ODD","provenance":"REAL_DSATM_PDF","session_count":1}],"counts":{"subjects":1,"faculty":1,"sections":6,"sessions":1,"inferred_rooms":0,"roomless_sessions":0},"conflicts":{"room":0,"faculty":0,"section":0}}
```

### `GET /timetable/date/{YYYY-MM-DD}`

Maps a date to its weekday and returns that date's active-term sessions. On a seeded holiday, sessions are omitted and `holiday` contains the holiday name. Any authenticated role may read it; maintenance receives only day and holiday metadata, not section sessions.

```json
{"date":"2026-11-10","weekday":"Tue","holiday":"Deepavali 2026","sessions":[]}
```

## Role summary

| Role | Read sections and room data | Own student record/timetable | Faculty timetable | Conflict report | Create/update sessions |
| --- | --- | --- | --- | --- | --- |
| `student` | Yes; section timetable limited to own section | Yes | No | No | No |
| `teaching_faculty` | Yes | No | Own only | No | No |
| `hod` | Yes | No | Own only | Yes | No |
| `admin` | Yes | No | Any | Yes | Yes |
| `maintenance` | Room data and metadata only; no roster, student timetable, or section timetable | No | No | No | No |

Unauthenticated requests return `401`. Authenticated requests outside the role or ownership rules return `403`. Student names and USNs are exposed only through the authenticated student's own endpoints; maintenance cannot read student roster or student timetables.

## Authentication endpoints

### `POST /auth/login`

Public endpoint. Request fields are `username` and `password`.

```json
{"username":"fac1","password":"Pass@123"}
```

Response fields are `access_token`, `token_type`, and `user`. The user object includes `id`, `username`, `full_name`, `role`, `category`, and `department`.

```json
{"access_token":"<JWT>","token_type":"bearer","user":{"id":4,"username":"fac1","full_name":"Synthetic Faculty 1","role":"teaching_faculty","category":"Faculty","department":"CSE"}}
```

Invalid credentials return `401` with `{"detail":"Invalid username or password"}`.

### `GET /auth/me`

Requires a bearer JWT. Returns the authenticated user object with `id`, `username`, `full_name`, `role`, `category`, and `department`.

```json
{"id":4,"username":"fac1","full_name":"Synthetic Faculty 1","role":"teaching_faculty","category":"Faculty","department":"CSE"}
```

## Error response shapes

Errors use FastAPI's `{"detail": ...}` envelope. Examples reflect the current backend:

```text
401: {"detail":"Not authenticated"}
403: {"detail":"Insufficient permissions"}
404: {"detail":"Room not found"}
409: {"detail":{"detail":"session clashes","conflict":{"type":"room","term_code":"2026-27-ODD","day":"Wed","period":1,"session_ids":[501,502]}}}
422: {"detail":[{"type":"missing","loc":["body","username"],"msg":"Field required","input":{}}]}
```

Each numeric prefix labels the HTTP status; the JSON after it is the actual response body. A version conflict uses `{"detail":{"detail":"version conflict","version":1}}`.

Roles are returned in the `role` field: `student`, `teaching_faculty`, `hod`, `admin`, or `maintenance`. Categories are returned in `category`: `Student`, `Faculty`, or `Management` (`hod` is categorized as `Faculty`).

## Floorplan and navigation endpoints (M3)

Floorplan geometry and navigation graph data are deterministic synthetic layout data with `provenance: "SYNTHETIC"`. Floors are `-1, 0, 1, 2, 3, 4, 5`, with a `1000 × 600` canvas, a central corridor at `y=270..330`, and rooms in two rows. Room colors use the section 7 palette: classroom `#93C5FD`, computer/hardware lab `#D8B4FE`, seminar/workshop `#86EFAC`, office `#FED7AA`, and utility/circulation `#CBD5E1` or `#E2E8F0`.

All endpoints in this section allow any authenticated role, including maintenance. Unauthenticated requests return `401`.

### `GET /floorplan`

Lists the available floors and canvas metadata.

```json
{"provenance":"SYNTHETIC","canvas":{"width":1000,"height":600,"metres_per_pixel":0.06},"floors":[{"floor":-1,"label":"Basement","room_count":4},{"floor":0,"label":"Ground Floor","room_count":10},{"floor":1,"label":"First Floor","room_count":10},{"floor":2,"label":"Second Floor","room_count":12},{"floor":3,"label":"Third Floor","room_count":10},{"floor":4,"label":"Fourth Floor","room_count":10},{"floor":5,"label":"Fifth Floor","room_count":10}]}
```

### `GET /floorplan/{floor}?day={day}&period={period}&date={YYYY-MM-DD}`

Returns the requested floor's room geometry, color, room `status`, `capacity_effective`, `data_status`, and occupancy. The `day` and `period` filters must be supplied together; alternatively, supply `date` with `period` to derive the weekday. With no time filter, occupancy is `null`. Occupancy is read from the active term's `timetable_sessions`. `capacity_effective` is the room capacity unless its status is `under_maintenance` or `temporarily_unavailable`, when it is zero. On the seeded Deepavali holiday, the response contains the holiday name and all rooms have no occupancy.

```json
{"floor":1,"label":"First Floor","canvas":{"width":1000,"height":600},"date":null,"weekday":"Wed","holiday":null,"rooms":[{"room_id":"A-F1-01","geometry":{"x":60,"y":40,"w":160,"h":210},"color":"#93C5FD","status":"available","capacity_effective":60,"data_status":"SYNTHETIC","occupancy":{"occupied":true,"sessions":[{"section_code":"E","batch":"ALL","periods":[1],"subject_code":"BCS502","raw_label":"Wed P1 ML @ A 101"}]}}]}
```

Holiday response example:

```json
{"floor":2,"label":"Second Floor","canvas":{"width":1000,"height":600},"date":"2026-11-10","weekday":"Tue","holiday":"Deepavali 2026","rooms":[{"room_id":"A-F2-02","geometry":{"x":60,"y":40,"w":130,"h":210},"color":"#93C5FD","status":"available","capacity_effective":60,"data_status":"SYNTHETIC","occupancy":{"occupied":false,"sessions":[]}}]}
```

Unknown floor IDs return `404`.

### `GET /nav/route?from={room}&to={room}&mode={stairs|lift|accessible}`

Finds a shortest route on the seeded corridor graph with Dijkstra's algorithm. `from` and `to` accept canonical room IDs or room aliases supported by `resolve_room`. Routes connect each room's door node to the corridor graph and never traverse room interiors. `stairs` permits stair-core links; `lift` and `accessible` permit lift-core links only. A same-room request returns a zero-weight route. Unknown rooms return `404`; an unsupported or missing mode returns `422`.

Edge `weight` and `route_cost_seconds` are modeled travel seconds. Horizontal edge distance uses 1000 px = 60 m and configured walking speed. Stairs model 12 m per floor. Lift edges model 8 m per floor plus a 20 second wait. `distance_m` is the sum of modeled distances, while waits contribute to cost but not distance. The returned route cost equals the sum of returned edge weights.

```json
{"from_room":"A-F1-01","to_room":"A-F1-02","mode":"stairs","node_keys":["f1_door_A-F1-01","f1_corridor_n1","f1_corridor_n2","f1_door_A-F1-02"],"edges":[{"from":"f1_door_A-F1-01","to":"f1_corridor_n1","mode":"corridor","distance_m":3,"wait_seconds":0,"weight":2.5},{"from":"f1_corridor_n1","to":"f1_corridor_n2","mode":"corridor","distance_m":12,"wait_seconds":0,"weight":10},{"from":"f1_corridor_n2","to":"f1_door_A-F1-02","mode":"corridor","distance_m":3,"wait_seconds":0,"weight":2.5}],"distance_m":18,"route_cost_seconds":15,"provenance":"SYNTHETIC"}
```

Same-room example:

```json
{"from_room":"A-F1-10","to_room":"A-F1-10","mode":"stairs","node_keys":["f1_door_A-F1-10"],"edges":[],"distance_m":0,"route_cost_seconds":0,"provenance":"SYNTHETIC"}
```

Navigation costs are configurable through `NAV_METRES_PER_PIXEL`, `NAV_STAIRS_METRES_PER_FLOOR`, `NAV_LIFT_METRES_PER_FLOOR`, `NAV_LIFT_WAIT_SECONDS`, and `NAV_WALKING_SPEED_MPS`.

## Energy and optimization endpoints (M5/M6)

All wattages, the `8.50 INR/kWh` tariff, and the optimization cost model are `SYNTHETIC`. Responses expose `data_status: "SYNTHETIC"` (derived room/session calculations may additionally report `INFERRED`). A period is 55 minutes by default (`period_hours = 55/60`); settings may override it. Unless configured otherwise, unoccupied standby use is zero. These endpoints never change official timetable rows during optimization; applying a proposal is a separate version-checked workflow.

### `GET /energy/baseline?term={term_code}`

Admin and HOD may read this report. Maintenance is denied. If `term` is omitted, the active term is used. `occupied_periods_week` counts unique occupied `(day, period)` slots per room, so a recorded same-room clash still counts that room once as on; clashes are separately counted. Sessions with `room_required: false` do not consume energy. The flat comparison uses the dataset's fixed 6 hours/day × 5 days/week assumption, not timetable occupancy.

```json
{
  "term_code":"2026-27-ODD",
  "period_hours":0.9166667,
  "tariff_inr_per_kwh":8.5,
  "data_status":"SYNTHETIC",
  "timetable_occupancy":{
    "rooms":[{"room_id":"A-F2-02","floor":2,"connected_kw":0.71,"occupied_periods_week":12,"kwh_week":7.82,"cost_week_inr":66.47,"data_status":"SYNTHETIC"}],
    "floors":[{"floor":2,"occupied_periods_week":12,"kwh_week":7.82,"cost_week_inr":66.47}],
    "block":{"occupied_periods_week":12,"kwh_week":7.82,"cost_week_inr":66.47},
    "recorded_room_clashes":2
  },
  "flat_spec_baseline_6h_x_5days":{
    "rooms":[{"room_id":"A-F2-02","kwh_week":21.3,"cost_week_inr":181.05}],
    "floors":[{"floor":2,"kwh_week":21.3,"cost_week_inr":181.05}],
    "block":{"kwh_week":21.3,"cost_week_inr":181.05},
    "label":"Fixed equipment load × 6 h/day × 5 days/week"
  }
}
```

### `GET /energy/utilization?term={term_code}`

Admin and HOD may read this report. Maintenance is denied. Occupancy percentage uses `periods_per_day × 6 days`; rooms with no occupied timetable periods are listed in `rooms_never_used`. Seat use is section strength divided by `capacity_effective`; batch sessions use half the section strength. `rooms_under_50_percent_seat_utilization` contains rooms with observed sessions and maximum observed seat utilization below 50%; rooms with unknown capacity are reported with `seat_utilization: null` and are not counted as below 50%.

```json
{
  "term_code":"2026-27-ODD",
  "periods_per_day":8,
  "days_per_week":6,
  "data_status":"INFERRED",
  "rooms":[{"room_id":"A-F2-02","occupied_periods_week":12,"available_periods_week":48,"occupancy_percent":25.0,"capacity_effective":60,"seat_utilization":0.5,"data_status":"INFERRED"}],
  "rooms_never_used":["A-F2-12"],
  "rooms_under_50_percent_seat_utilization":[{"room_id":"A-F2-03","seat_utilization":0.25}]
}
```

### `POST /optimizer/energy`

Admin only. Creates and returns a draft proposal; it does not modify official timetable sessions. `movable` is `inferred_only` (default when omitted), `all`, or `selected_sections`; `sections` is a list of section codes used for `selected_sections`. `max_relocations` is null or a nonnegative integer; `lock_labs` defaults true; `forbid_floors` is a list of integer floor numbers; `forbid_rooms` is a list of canonical room IDs; `close_floors` and `close_rooms` are optional additive fields, defaulting to empty lists. When a closure is supplied, every room-required session currently assigned there must leave; every other session stays fixed. Closed resources are forbidden as destinations. A lab session remains locked when `lock_labs` is true; if a closure requires moving such a lab, the solve returns `INFEASIBLE` with `infeasible_reason`. `lambda_move` and `lambda_floor` are nonnegative objective weights; `time_limit_s` defaults to 30; `seed` defaults to 0.

```json
{
  "term":"2026-27-ODD",
  "movable":"inferred_only",
  "sections":[],
  "max_relocations":10,
  "lock_labs":true,
  "forbid_floors":[5],
  "forbid_rooms":["A-F2-11"],
  "close_floors":[],
  "close_rooms":[],
  "lambda_move":1.0,
  "lambda_floor":0.25,
  "time_limit_s":30,
  "seed":0
}
```

Response is a persisted draft and includes the independent validator result. `solver_status` is `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `MODEL_INVALID`, or `UNKNOWN`. Fixed-vs-fixed source clashes appear in `unresolvable_source_clashes`; they remain unchanged. The response records the OR-Tools version, time limit, seed, and one-worker deterministic configuration.

```json
{
  "id":"proposal-uuid",
  "status":"draft",
  "term_code":"2026-27-ODD",
  "solver_status":"OPTIMAL",
  "solve_time_s":0.42,
  "ortools_version":"x.y.z",
  "time_limit_s":30,
  "seed":0,
  "num_workers":1,
  "objective_value":123.45,
  "objective":"minimize weekly room-on kWh × synthetic tariff + lambda_move × relocations + lambda_floor × students × floors changed",
  "before":{"kwh_week":100.0,"cost_week_inr":850.0,"clash_count":4},
  "after":{"kwh_week":82.0,"cost_week_inr":697.0,"clash_count":2},
  "relocations":3,
  "affected_students":120,
  "affected_sections":["A","C"],
  "changes":[{"session_id":501,"from_room":"A-F2-02","to_room":"A-F1-03","expected_session_version":1,"expected_from_room_version":1,"expected_to_room_version":1}],
  "unresolvable_source_clashes":[{"type":"room","day":"Thu","period":4,"session_ids":[601,602]}],
  "validator":{"valid":true,"violations":[]},
  "data_status":"SYNTHETIC"
}
```

An infeasible solve returns a persisted draft with `solver_status: "INFEASIBLE"`, no assignment changes, an empty `changes` list, and `infeasible_reason` when a binding reason can be identified. Constraints are never relaxed silently. The response uses the same metadata fields and contains the unchanged `before`/`after` values.

### Proposal workflow

`POST /proposals/{proposal_id}/submit`, `/approve`, `/reject`, and `/apply` use an empty JSON object `{}`. Admin may submit, reject, and apply. Admin may approve any proposal; HOD may approve only if every affected section belongs to their department. All authenticated roles may list and inspect proposals with `GET /proposals` and `GET /proposals/{proposal_id}`; student and maintenance roster restrictions remain in effect and proposal responses contain no student names or USNs. Submit moves a draft to submitted, approve moves it to approved, reject moves it to rejected, and apply moves an approved proposal to applied. Rejected/discarded proposals do not change timetable rows. Apply atomically checks the stored expected version of every changed session and source/destination room, updates room assignments and increments each changed session version; a stale version returns `409` and rolls back all changes.

```json
{"id":"proposal-uuid","status":"submitted","term_code":"2026-27-ODD","data_status":"SYNTHETIC"}
```

`GET /proposals` returns `[{"id":"proposal-uuid","status":"draft","term_code":"2026-27-ODD","solver_status":"OPTIMAL","data_status":"SYNTHETIC"}]`. `GET /proposals/{proposal_id}` returns the full optimizer response above plus workflow status. Unknown proposal IDs return `404`.

### Energy and proposal errors / permissions

Unauthenticated requests return `401` with `{"detail":"Not authenticated"}`. Authenticated roles without permission return `403` with `{"detail":"Insufficient permissions"}`. Unknown terms or proposal IDs return `404` with `{"detail":"Term not found"}` or `{"detail":"Proposal not found"}`. Stale versions while applying return `409` with `{"detail":"version conflict"}` and no timetable changes. Invalid fields (including negative relocation/time/weights or invalid `movable`) return `422` with FastAPI's `{"detail":[{"type":"...","loc":[...],"msg":"...","input":...}]}` shape.

| Endpoint | student | teaching_faculty | hod | admin | maintenance |
| --- | --- | --- | --- | --- | --- |
| `GET /energy/baseline`, `GET /energy/utilization` | 403 | 403 | Read | Read | 403 |
| `POST /optimizer/energy` | 403 | 403 | 403 | Draft | 403 |
| `GET /proposals`, `GET /proposals/{id}` | Read | Read | Read | Read | Read |
| `POST /proposals/{id}/submit`, `/reject`, `/apply` | 403 | 403 | 403 | Yes | 403 |
| `POST /proposals/{id}/approve` | 403 | 403 | Own department only | Yes | 403 |
