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

### `GET /rooms?status_filter={status}`

Lists rooms; `status_filter` is optional. Any authenticated role may read the list. The response retains all existing `RoomOut` fields and adds `real_label`, `aliases`, `data_status`, and `capacity_effective`. `real_label` is the room's dataset name (`Room.name`), `aliases` is the list of resolver aliases, and `data_status` mirrors the existing provenance status. `capacity_effective` is zero for `under_maintenance` and `temporarily_unavailable` rooms, and otherwise equals `capacity`. The same additive fields are returned by other endpoints using `RoomOut`.

Example item from a real seeded `GET /rooms` response (room values are dataset/seed values):

```json
{"id":24,"building_id":1,"number":"A-F1-10","floor":1,"capacity":30,"room_type":"Empty Room","facilities":"","status":"available","version":1,"provenance":"SYNTHETIC","real_label":"Empty Room 10","aliases":["110","A-108"],"data_status":"SYNTHETIC","capacity_effective":30}
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

Returns the requested floor's existing floor metadata and room geometry, color, `status`, `capacity_effective`, `data_status`, and occupancy. Existing response fields are retained. It adds:

- `cores`: the west stair, center lift, and east stair blocks, each with `x`, `y`, `w`, `h`, and display `label`. Core blocks align with the corresponding navigation core nodes in the corridor.
- `nav_nodes`: every navigation node on the requested floor, with `node_key`, `kind` (the stored node type), `floor`, `x`, `y`, and a display `label`. This includes door, corridor, stair, and lift nodes.
- Per room, `real_label` (the dataset room name) and `aliases` (resolver aliases). `data_status` remains present and mirrors room provenance.

The `day` and `period` filters must be supplied together; alternatively, supply `date` with `period` to derive the weekday. With no time filter, occupancy is `null`. Occupancy is read from the active term's `timetable_sessions`. `capacity_effective` is zero for `under_maintenance` and `temporarily_unavailable` rooms and otherwise equals `capacity`. On the seeded Deepavali holiday, the response contains the holiday name and all rooms have no occupancy.

The following real response excerpt is from `GET /floorplan/3?day=Wed&period=1`; only the representative room and navigation nodes needed to illustrate the added fields are shown. The endpoint returns all rooms and navigation nodes for that floor.

```json
{"floor":3,"label":"Third Floor","canvas":{"width":1000,"height":600},"date":null,"weekday":"Wed","holiday":null,"cores":[{"x":60,"y":270,"w":80,"h":60,"label":"West stairs"},{"x":460,"y":270,"w":80,"h":60,"label":"Center lift"},{"x":860,"y":270,"w":80,"h":60,"label":"East stairs"}],"nav_nodes":[{"node_key":"f3_stairs_core_west","kind":"stairs_core_west","floor":3,"x":100,"y":300,"label":"West stairs"},{"node_key":"f3_lifts_core_center","kind":"lifts_core_center","floor":3,"x":500,"y":300,"label":"Center lift"},{"node_key":"f3_stairs_core_east","kind":"stairs_core_east","floor":3,"x":900,"y":300,"label":"East stairs"},{"node_key":"f3_corridor_n5","kind":"corridor_n5","floor":3,"x":900,"y":300,"label":"Corridor N5"},{"node_key":"f3_door_A-F3-05","kind":"door","floor":3,"x":900,"y":250,"label":"Door A-F3-05"}],"rooms":[{"room_id":"A-F3-05","geometry":{"x":780.0,"y":40,"w":160.0,"h":210},"color":"#D8B4FE","status":"available","capacity_effective":30,"data_status":"SYNTHETIC","real_label":"Computer Lab 05","aliases":["305"],"occupancy":{"occupied":false,"sessions":[]}}]}
```

Holiday response example:

```json
{"floor":2,"label":"Second Floor","canvas":{"width":1000,"height":600},"date":"2026-11-10","weekday":"Tue","holiday":"Deepavali 2026","rooms":[{"room_id":"A-F2-02","geometry":{"x":60,"y":40,"w":130,"h":210},"color":"#93C5FD","status":"available","capacity_effective":60,"data_status":"SYNTHETIC","occupancy":{"occupied":false,"sessions":[]}}]}
```

Unknown floor IDs return `404`.

### `GET /nav/route?from={room}&to={room}&mode={stairs|lift|accessible}`

Finds a shortest route on the seeded corridor graph with Dijkstra's algorithm. `from` and `to` accept canonical room IDs or room aliases supported by `resolve_room`. Routes connect each room's door node to the corridor graph and never traverse room interiors. `stairs` permits stair-core links; `lift` and `accessible` permit lift-core links only. A same-room request returns a zero-weight route. Unknown rooms return `404`; an unsupported or missing mode returns `422`.

The route keeps the existing `node_keys`, `edges`, `distance_m`, `route_cost_seconds`, and provenance fields. It adds `path`, an ordered list with each path node's `node_key`, `floor`, `x`, `y`, `kind`, and display `label`; `steps`, one item per edge with `instruction`, destination `floor`, `from_node`, `to_node`, `distance_m`, and `kind`; and `floors_visited`, the unique floors in path order. A stair/lift step's `floor` is its destination floor; a corridor/door step uses the destination node's floor. `kind` is the edge mode (`corridor`, `stairs`, or `lift`). Step distances sum to `distance_m`. A same-room route has one path node, no steps, and the room floor in `floors_visited`.

Edge `weight` and `route_cost_seconds` are modeled travel seconds. Horizontal edge distance uses 1000 px = 60 m and configured walking speed. Stairs model 12 m per floor. Lift edges model 8 m per floor plus a 20 second wait. `distance_m` is the sum of modeled distances, while waits contribute to cost but not distance. The returned route cost equals the sum of returned edge weights.

```json
{"from_room":"A-F1-10","to_room":"A-F3-05","mode":"lift","node_keys":["f1_door_A-F1-10","f1_corridor_n5","f1_corridor_n4","f1_corridor_n3","f1_lifts_core_center","f2_lifts_core_center","f3_lifts_core_center","f3_corridor_n3","f3_corridor_n4","f3_corridor_n5","f3_door_A-F3-05"],"edges":[{"from":"f1_door_A-F1-10","to":"f1_corridor_n5","mode":"corridor","distance_m":3.0,"wait_seconds":0.0,"weight":2.5},{"from":"f1_corridor_n5","to":"f1_corridor_n4","mode":"corridor","distance_m":12.0,"wait_seconds":0.0,"weight":10.0},{"from":"f1_corridor_n4","to":"f1_corridor_n3","mode":"corridor","distance_m":12.0,"wait_seconds":0.0,"weight":10.0},{"from":"f1_corridor_n3","to":"f1_lifts_core_center","mode":"corridor","distance_m":0.0,"wait_seconds":0.0,"weight":0.0},{"from":"f1_lifts_core_center","to":"f2_lifts_core_center","mode":"lift","distance_m":8.0,"wait_seconds":20.0,"weight":26.6667},{"from":"f2_lifts_core_center","to":"f3_lifts_core_center","mode":"lift","distance_m":8.0,"wait_seconds":20.0,"weight":26.6667},{"from":"f3_lifts_core_center","to":"f3_corridor_n3","mode":"corridor","distance_m":0.0,"wait_seconds":0.0,"weight":0.0},{"from":"f3_corridor_n3","to":"f3_corridor_n4","mode":"corridor","distance_m":12.0,"wait_seconds":0.0,"weight":10.0},{"from":"f3_corridor_n4","to":"f3_corridor_n5","mode":"corridor","distance_m":12.0,"wait_seconds":0.0,"weight":10.0},{"from":"f3_corridor_n5","to":"f3_door_A-F3-05","mode":"corridor","distance_m":3.0,"wait_seconds":0.0,"weight":2.5}],"distance_m":70.0,"route_cost_seconds":98.3334,"provenance":"SYNTHETIC","path":[{"node_key":"f1_door_A-F1-10","floor":1,"x":900,"y":350,"kind":"door","label":"Door A-F1-10"},{"node_key":"f1_corridor_n5","floor":1,"x":900,"y":300,"kind":"corridor_n5","label":"Corridor N5"},{"node_key":"f1_corridor_n4","floor":1,"x":700,"y":300,"kind":"corridor_n4","label":"Corridor N4"},{"node_key":"f1_corridor_n3","floor":1,"x":500,"y":300,"kind":"corridor_n3","label":"Corridor N3"},{"node_key":"f1_lifts_core_center","floor":1,"x":500,"y":300,"kind":"lifts_core_center","label":"Center lift"},{"node_key":"f2_lifts_core_center","floor":2,"x":500,"y":300,"kind":"lifts_core_center","label":"Center lift"},{"node_key":"f3_lifts_core_center","floor":3,"x":500,"y":300,"kind":"lifts_core_center","label":"Center lift"},{"node_key":"f3_corridor_n3","floor":3,"x":500,"y":300,"kind":"corridor_n3","label":"Corridor N3"},{"node_key":"f3_corridor_n4","floor":3,"x":700,"y":300,"kind":"corridor_n4","label":"Corridor N4"},{"node_key":"f3_corridor_n5","floor":3,"x":900,"y":300,"kind":"corridor_n5","label":"Corridor N5"},{"node_key":"f3_door_A-F3-05","floor":3,"x":900,"y":250,"kind":"door","label":"Door A-F3-05"}],"steps":[{"instruction":"Walk from Door A-F1-10 to Corridor N5","floor":1,"from_node":"f1_door_A-F1-10","to_node":"f1_corridor_n5","distance_m":3.0,"kind":"corridor"},{"instruction":"Walk from Corridor N5 to Corridor N4","floor":1,"from_node":"f1_corridor_n5","to_node":"f1_corridor_n4","distance_m":12.0,"kind":"corridor"},{"instruction":"Walk from Corridor N4 to Corridor N3","floor":1,"from_node":"f1_corridor_n4","to_node":"f1_corridor_n3","distance_m":12.0,"kind":"corridor"},{"instruction":"Walk from Corridor N3 to Center lift","floor":1,"from_node":"f1_corridor_n3","to_node":"f1_lifts_core_center","distance_m":0.0,"kind":"corridor"},{"instruction":"Take the lift to Floor 2","floor":2,"from_node":"f1_lifts_core_center","to_node":"f2_lifts_core_center","distance_m":8.0,"kind":"lift"},{"instruction":"Take the lift to Floor 3","floor":3,"from_node":"f2_lifts_core_center","to_node":"f3_lifts_core_center","distance_m":8.0,"kind":"lift"},{"instruction":"Walk from Center lift to Corridor N3","floor":3,"from_node":"f3_lifts_core_center","to_node":"f3_corridor_n3","distance_m":0.0,"kind":"corridor"},{"instruction":"Walk from Corridor N3 to Corridor N4","floor":3,"from_node":"f3_corridor_n3","to_node":"f3_corridor_n4","distance_m":12.0,"kind":"corridor"},{"instruction":"Walk from Corridor N4 to Corridor N5","floor":3,"from_node":"f3_corridor_n4","to_node":"f3_corridor_n5","distance_m":12.0,"kind":"corridor"},{"instruction":"Walk from Corridor N5 to Door A-F3-05","floor":3,"from_node":"f3_corridor_n5","to_node":"f3_door_A-F3-05","distance_m":3.0,"kind":"corridor"}],"floors_visited":[1,2,3]}
```

Same-room example (new route fields included):

```json
{"from_room":"A-F1-10","to_room":"A-F1-10","mode":"accessible","node_keys":["f1_door_A-F1-10"],"edges":[],"distance_m":0,"route_cost_seconds":0,"provenance":"SYNTHETIC","path":[{"node_key":"f1_door_A-F1-10","floor":1,"x":900,"y":350,"kind":"door","label":"Door A-F1-10"}],"steps":[],"floors_visited":[1]}
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

## M7 ERP, timetable, calendar, and navigation additions

These additions preserve all existing response fields and meanings. All examples use synthetic or redacted identifiers; no real student identity is included. `data_status: "SYNTHETIC"` identifies generated attendance, fee, scholarship, and LMS demo content.

### Room list and availability additions

`GET /rooms` keeps its existing `RoomOut` fields and adds `timetable_eligible` so clients can see which rooms are scheduled for teaching. Its existing optional `status_filter` remains unchanged. `capacity` is the supplied dataset capacity, which is synthetic for these room records; no separate observed `capacity_real` value is available.

`GET /rooms/availability?day={day}&period={period}&term={term}&include_non_timetable={bool}` adds optional `include_non_timetable`, default `false`. By default only timetable-eligible rooms are listed; `true` includes non-timetable rooms as well. `term` still selects the term used to calculate occupied slots. Room status and capacity are not additional availability filters. Response envelope and room fields retain the existing availability shape.

```json
{"day":"Wed","period":1,"term_code":"2026-27-ODD","rooms":[{"room_id":"A-F2-02","available":false,"session_ids":[501],"provenance":"SYNTHETIC"}]}
```

### Timetable session additive fields

Every session returned by section, student, faculty, room, and date timetable endpoints retains its current fields and adds:

- `session_type`: `Lecture`, `Lab`, or `Activity`.
- `start_time`, `end_time`: 24-hour `HH:MM` strings from the period grid. End time is the end of the last occupied period.
- `faculty_names`: ordered display-name list for every linked faculty member.
- `faculty_details`: same-order `{name, data_status}` entries; ordinary names use their current provenance, and the section-E ERP-only display name uses `REAL_ERP_SCREENSHOT`.
- `room_real_label`: room dataset label, or `null` for a roomless session.
- `room_inferred`: whether the session's room assignment is inferred.

Existing `faculty_name`, `room_id`, `provenance`, and all other response fields remain unchanged. Activity subjects include NPTEL/MOOC, PRE-PLACEMENT, NSS/YOGA, and Skill Dev; lab batches and lab subjects use `Lab`; other sessions use `Lecture`. Sessions sharing one multi-period block retain the same `block_id`.

```json
{"id":501,"term_code":"2026-27-ODD","section_code":"E","batch":"ALL","day":"Wed","periods":[1,2],"subject_code":"BCS502","subject_name":"Machine Learning","faculty_id":31,"faculty_initials":"PP","faculty_name":"Parvathisha Pudugosala","faculty_names":["Parvathisha Pudugosala"],"faculty_details":[{"name":"Parvathisha Pudugosala","data_status":"REAL_DSATM_PDF"}],"room_id":"A-F2-02","room_real_label":"Classroom 02","room_inferred":true,"room_required":true,"raw_label":"5TH E SECTION; P1-P2 ML (PP)","block_id":"2026-27-ODD-E-WED-P1-P2-1","session_type":"Lecture","start_time":"09:30","end_time":"11:20","provenance":"REAL_DSATM_PDF","version":1}
```

### `GET /meta/periods`

Any authenticated role. Returns the period grid and breaks.

```json
{"periods":[{"period":1,"start":"09:30","end":"10:25"},{"period":2,"start":"10:25","end":"11:20"},{"period":3,"start":"11:35","end":"12:30"},{"period":4,"start":"12:30","end":"13:25"},{"period":5,"start":"14:15","end":"15:10"},{"period":6,"start":"15:10","end":"16:05"},{"period":7,"start":"16:05","end":"17:00"}],"breaks":[{"after_period":2,"label":"Tea","start":"11:20","end":"11:35"},{"after_period":4,"label":"Lunch","start":"13:25","end":"14:15"}]}
```

### Holidays and calendar

#### `GET /calendar/holidays`

Any authenticated role. Returns only the two confirmed entries currently in the seed. No other holidays are implied.

```json
[{"date":"2026-11-10","name":"Deepavali 2026","source":"M1"},{"date":"2026-11-27","name":"Kanaka Jayanthi","source":"ERP_SCREENSHOT"}]
```

#### `GET /calendar/summary`

Any authenticated role. Terms have unknown boundaries; `start_date` and `end_date` are `null` and the response note explicitly says the dates are not known.

```json
{"holidays":[{"date":"2026-11-10","name":"Deepavali 2026","source":"M1"},{"date":"2026-11-27","name":"Kanaka Jayanthi","source":"ERP_SCREENSHOT"}],"terms":[{"term_code":"2026-27-ODD","start_date":null,"end_date":null}],"note":"Term start and end dates are not known."}
```

`GET /timetable/date/{YYYY-MM-DD}` keeps its current shape. For either seeded holiday, `holiday` is the holiday name and `sessions` is empty. The 2026-11-10 Deepavali behavior is unchanged; 2026-11-27 returns `"Kanaka Jayanthi"` in `holiday`.

### Navigation instruction additions

`GET /nav/route?from={room}&to={room}&mode={stairs|lift|accessible}` keeps `path`, `steps`, `node_keys`, `edges`, `floors_visited`, and every existing field unchanged. It adds `instructions` and `summary`.

Each instruction has `{index, kind, text, floor, to_floor, distance_m, path_from_index, path_to_index}`. `kind` is `start`, `walk`, `stairs`, `lift`, or `arrive`; indexes are inclusive indexes into `path`. Corridor runs on one floor become one `walk`. A vertical transition is one stair/lift instruction. Instruction text uses room/core display labels and floor names, never raw graph node keys. Accessible routes contain no `stairs` instruction. The first instruction is `Leave …`, and the final instruction is `You have arrived at …`; for the same room only the `arrive` instruction is returned.

`summary` has `{distance_m, est_seconds, est_minutes, floors_traversed, floors_changed, mode, start, end}`. `start` and `end` each have `{code, real_label, floor}`. `est_minutes` is rounded up; instruction distances sum to the unchanged top-level `distance_m` within 0.5 m.

Example of the real accessible route `A-G06` to `A-F5-05`; coordinates and node keys stay in the existing `path` field, omitted here to focus on the new fields:

```json
{"instructions":[{"index":0,"kind":"start","text":"Leave Staff Room 06 (A-G06)","floor":0,"to_floor":null,"distance_m":0,"path_from_index":0,"path_to_index":0},{"index":1,"kind":"walk","text":"Walk 27 m along the Ground Floor corridor towards the Lift.","floor":0,"to_floor":null,"distance_m":27,"path_from_index":0,"path_to_index":4},{"index":2,"kind":"lift","text":"Take the Lift up 5 floors to Floor 5.","floor":0,"to_floor":5,"distance_m":40,"path_from_index":4,"path_to_index":9},{"index":3,"kind":"walk","text":"Walk 27 m along the Floor 5 corridor towards Computer Lab 05 (A-F5-05).","floor":5,"to_floor":null,"distance_m":27,"path_from_index":9,"path_to_index":13},{"index":4,"kind":"arrive","text":"You have arrived at Computer Lab 05 (A-F5-05)","floor":5,"to_floor":null,"distance_m":0,"path_from_index":13,"path_to_index":13}],"summary":{"distance_m":94,"est_seconds":178.3335,"est_minutes":3,"floors_traversed":[0,1,2,3,4,5],"floors_changed":5,"mode":"accessible","start":{"code":"A-G06","real_label":"Staff Room 06","floor":0},"end":{"code":"A-F5-05","real_label":"Computer Lab 05","floor":5}}}
```

### ERP-style synthetic student demo endpoints

All five endpoints below are student-only, derive the student solely from the bearer token, accept no student identifier, and return `data_status: "SYNTHETIC"`. Non-students receive `403`; missing/invalid authentication receives `401`. These are generated demo values, not official student records. No phone, email, parent, photo, attendance-source, or uploaded-content fields are provided.

#### `GET /students/me/profile`

```json
{"usn":"<authenticated student's own USN>","full_name":"<authenticated student's own roster name>","branch":"CS","department":"CSE","semester":5,"division":"CSE-5","section_label":"CS-5-E","section_mapping_status":"INFERRED","lab_batch":"A1","roll_no":null,"home_room":{"code":"A-F5-02","real_label":"Classroom 02"},"data_status":"SYNTHETIC"}
```

#### `GET /students/me/attendance?from={YYYY-MM-DD}&to={YYYY-MM-DD}`

Dates default from configured `demo_attendance_start` (default 2026-10-01) through yesterday. Only past Monday–Saturday dates are returned. One timetable entry, including a multi-period block, is one slot. A holiday or day without sessions has a placeholder slot with status `-`; these placeholders do not count as attendance. Statuses `P`, `A`, and `NA` are stateless deterministic values derived from SHA-256 of the USN, date, slot key, subject, and configured demo salt. About 3% are `NA`; the remaining values use a deterministic subject probability between 0.72 and 0.96.

```json
{"data_status":"SYNTHETIC","days":[{"date":"2026-11-20","weekday":"Fri","slots":[{"slot":"P1","subject_code":"BCS515B","subject_name":"Cryptography & Network Security","status":"P"}]},{"date":"2026-11-21","weekday":"Sat","slots":[{"slot":null,"subject_code":null,"subject_name":null,"status":"-"}]}]}
```

#### `GET /students/me/attendance/summary`

Computed from the same generated grid as the attendance endpoint. Percent is present divided by present plus absent, excluding `NA`; percentages are rounded to two decimals. `status` is `low` below 75%.

```json
{"data_status":"SYNTHETIC","overall":{"present":1,"absent":0,"no_attendance":0,"total":1,"percent":100.0},"subjects":[{"subject_code":"BCS515B","subject_name":"Cryptography & Network Security","component":"Theory","total":1,"present":1,"percent":100.0,"status":"ok"}]}
```

#### `GET /students/me/lms/subjects`

Returns the nine semester-5 subjects for the authenticated student's mapped section, with dataset subject codes kept in `subject_code` and ERP alternatives in `alt_code`. It returns no marks or uploads.

```json
{"data_status":"SYNTHETIC","subjects":[{"subject_code":"BCS515B","alt_code":"BCS504B","subject_name":"Cryptography & Network Security","component":"Theory","semester":5,"faculty_names":["<display name>"]}]}
```

#### `GET /students/me/fees`

All amounts and receipt entries are fictional, round settings-based placeholders. Receipt numbers use only the `SYN-` synthetic namespace; receipt mode is `SYNTHETIC`.

```json
{"data_status":"SYNTHETIC","ledger":{"to_be_collected":360000,"paid":240000,"previous":0,"pending":120000},"years":[{"year":1,"total":120000,"receipts":[{"receipt_no":"SYN-0001","date":"2024-06-01","heads":[{"name":"Tuition","amount":100000},{"name":"Academic","amount":10000},{"name":"Examination","amount":5000},{"name":"University","amount":3000},{"name":"Skill Lab","amount":2000}],"mode":"SYNTHETIC"}]}],"scholarship":{"status":"Not applicable","note":"Synthetic demo"}}
```

The fees example abbreviates the years list; the real response has years 1, 2, and 3. The attendance example abbreviates the date range. Those generated values are deterministic for the authenticated token and current configuration; they are not stored in database rows.
