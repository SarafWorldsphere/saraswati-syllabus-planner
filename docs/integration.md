# Integrating the Syllabus Planner

This service is an HTTP API. The admin, headmaster, and teacher screens do not live here. A dashboard calls `http://<host>:8010/api/v1`. Swagger at `/docs` is the field-level contract. This page is how to wire a caller. Screen layouts are in [docs/wireframes](wireframes/README.md).

Python 3.12 is required for the pinned dependencies. Python 3.14 cannot build them.

## Call shape

| | |
| --- | --- |
| Base | `/api/v1` |
| Auth | `Authorization: Bearer <token>` |
| School | `Host` header. The tenant kit resolves the school. There is no school id in the path. |
| JSON | snake_case |
| Dates | `YYYY-MM-DD` |
| Lists | `{"items": [...], "total": N}` |

`class_id` is a query parameter when the caller is narrowing a list, and a field in the body when a row is being written. Do not send `X-Class-Id`. The service ignores that header. One teacher often has periods in several classes on the same day, and a school-wide coverage call is supposed to omit the class.

## Who the caller is

Login decides the role. This service only reads it. Accepted role names are `School Admin`, `Headmaster`, and `Faculty`. `Admin` is treated as School Admin. `Teacher` is treated as Faculty. Any other role is 401. A known role on a route it cannot call is 403.

A real token is an HS256 JWT signed with this service's `SECRET_KEY`. Claims:

```json
{
  "role": "Faculty",
  "sub": "teacher-42",
  "tenant_id": "11111111-1111-4111-8111-111111111111",
  "exp": 1760000000
}
```

`sub` is stored as `created_by`, `updated_by`, and `teacher_id`. `tenant_id` must be the school the host resolved. A mismatch is 401.

Until `sgs-frontend` mints this token, Swagger accepts three bearer strings when `APP_ENV=development`:

| Bearer | Role |
| --- | --- |
| `dev-admin` | School Admin |
| `dev-headmaster` | Headmaster |
| `dev-faculty` | Faculty |

In development every host, including `localhost`, is school `DEV_TENANT_ID`. Production resolves the host from `platform.tenant_domains` and ignores that setting.

Class scope is not on the token and is not checked. The same Faculty role will mean a different authority in each class. That claim has to be added at login, in `sgs-frontend` `auth.ts` and `app/api/sso-token/route.ts`. This service will then only check the claim. Do not add a class lookup here.

## What each screen calls

Headmaster and School Admin write the plan. Faculty reads it and records the day. Coverage and closing an alert are Headmaster and Admin.

### Admin or Headmaster, once a year

1. `POST /boards`, grades, subjects, `POST /calendars`, blocks, then `POST /boards/{board_id}/calendars` to recommend that calendar. A calendar body has no `board_id`. Two boards can share one set of dates.
2. `POST /syllabus-items`. A topic that does not fit in one block sends `spans`: segment 1 is `planned`, later segments are `continues`. Omit `spans` and the server splits the topic across the board's default calendar.
3. `POST /academic-year` with both `board_id` (what is taught) and `calendar_id` (when). Opening a new active year closes the previous one.
4. `POST /holidays` for days this school is closed that the calendar did not list.
5. `POST /syllabus-plan/generate` with `class_id` and `subject_id`. Existing rows are left alone. The response is `{created, skipped}`. Without `class_master` and `subject_master` in this database, both ids are required.
6. `GET /syllabus-plan/unmatched` for topics whose `chapter_id` is still null. When `chapter_master` exists, the row includes a suggested chapter. `PATCH /syllabus-plan/{plan_id}` saves the match.

A plan write must send the `version_no` last read. The row moves to the next version and appends `syllabus_plan_audit`. An older version is 409. There is no delete. `is_active: false` turns a chapter off.

A topic the board never listed is `POST /syllabus-plan`. That row has `source: "admin"` and `syllabus_item_id: null`.

### Headmaster, during the term

- `GET /coverage` and `GET /coverage/detail?class_id=&subject_id=`. Status is `on_track` at 90% or above, `behind` from 70 to 89, `critical` below 70.
- `against_board` counts board topics whose first block has ended and that are still not fully taught. `admin_approved` counts topics an admin added. Those are separate from a delay.
- `GET /teacher-alerts` and `PATCH /teacher-alerts/{alert_id}` with `status` of `open`, `acknowledged`, or `closed`. `closed_by` comes from the token.

### Faculty, each teaching day

- `GET /syllabus-plan/mine?class_id=&subject_id=` to show the plan. This route does not write.
- `GET /teaching-log/today`. When the school `timetable` table is present, periods she has not marked yet are prefilled. Sunday, and any date in `school_holiday`, comes back with `is_working_day: false`.
- `POST /teaching-log` with the date and `entries`. Each entry carries its own `class_id`. The same class, date, and period updates the existing row. `status` is `taught`, `partly`, or `not_taken`. `not_taken` is an honest mark. It is not a missed day.
- `POST /lesson-plans/current` with only `class_id` and `subject_id`. Do not send a chapter name. The current topic is the first active plan row, in `plan_seq`, that is not fully taught. A null `planned_periods` is finished by one `taught`. `partly` and `not_taken` do not finish it. The faculty lesson-planner screen should call this instead of asking the teacher to type a chapter.

### Auto test

`GET /syllabus-plan/covered?class_id=&subject_id=&template_id=` returns topics with at least one `taught` mark. `template_id` limits that to the blocks the assessment covers. Auto test should call this instead of choosing chapters itself.

## A streak

A streak is one run of consecutive working days on which the timetable gave the teacher a period and she left the teaching log empty. Sunday and a school holiday are skipped. A day she marked, including `not_taken`, ends the run.

`missed_days` on `GET /teacher-alerts` is the length of the current run, counted at that moment. It is not stored. The only stored row is `marking_review`, created the first time the run reaches three days. `first_missed_date` is the first unmarked day of that run. Closing the row does not stop a later run from raising a new one. If she marks tonight, `missed_days` becomes 0 and the row stays open until the headmaster closes it.

Without a `timetable` table the alert list is empty. The service will not invent missed days.

## Sample calls

After `python scripts/bootstrap.py`, class `1` and subject `1` have Real Numbers at plan version 1, starting in July and continuing in August.

```bash
curl -s -H "Authorization: Bearer dev-admin" \
  http://localhost:8010/api/v1/calendars
```

The calendar object has no `board_id`.

```bash
curl -s -X PATCH -H "Authorization: Bearer dev-admin" \
  -H "Content-Type: application/json" \
  -d '{"version_no": 1, "chapter_id": 10}' \
  http://localhost:8010/api/v1/syllabus-plan/1
```

Sending `version_no: 1` again after that succeeds is 409.

```bash
curl -s -X POST -H "Authorization: Bearer dev-faculty" \
  -H "Content-Type: application/json" \
  -d '{"class_id": 1, "subject_id": 1}' \
  http://localhost:8010/api/v1/lesson-plans/current
```

The body is a plan for Real Numbers only. When `AI_SERVICE_URL` is set, the text comes from the faculty generator at `POST {AI_SERVICE_URL}/api/v1/ai/teacher/lesson-plan`. When it is empty, the route still returns a plan for that same topic.

## Tables this service does not own

`class_master`, `subject_master`, `chapter_master`, and `timetable` belong to the school. This API reads them when they are in the same database and does not create them. Chapter ids on the plan are loose references, not foreign keys, so the sample database can run without those masters.

School rows (`school_year`, `school_holiday`, `syllabus_plan`, `syllabus_plan_segment`, `syllabus_plan_audit`, `teaching_log`, `marking_review`) carry `tenant_id` and a `tenant_isolation` policy. Platform rows (board, calendar, syllabus item, assessment) have no tenant. The docker user is a superuser and bypasses the policy. A restricted role sees only the school on the transaction.

## Still to wire

- Dashboards. Each screen calls the routes above. This process does not render them.
- Login. `sgs-frontend` `app/api/sso-token/route.ts` sends Faculty to the faculty backend and School Admin to the admin backend. Headmaster returns no token. None of those targets is this service. Add a syllabus-planner SSO URL that asks this service to mint the JWT above. Login must not hold this service's `SECRET_KEY`.
- Class scope on that token, resolved once at login.
- Faculty lesson planner calls `POST /lesson-plans/current`.
- Auto test calls `GET /syllabus-plan/covered`.
