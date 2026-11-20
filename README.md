# Syllabus Planner

An HTTP API for the school syllabus. It does not serve the teacher, admin, or headmaster screens. Those dashboards come later and will call this process.

Swagger is the contract developers call against. The three PDFs in this folder are the original design notes. How a dashboard, login, or the faculty lesson planner should call this service is in [docs/integration.md](docs/integration.md).

## How to run

1. Start Postgres.

   ```bash
   docker compose up -d
   ```

   The database listens on port **5434** (`syllabus_planner` / user `swais`). The faculty stack already uses 5433.

2. Copy the environment file and install dependencies.

   ```bash
   cp .env.example .env
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   Use Python 3.12. The pinned Pydantic release does not install on Python 3.14. `saraswati-tenant` comes from the tenant kit. For a local checkout instead of GitHub:

   ```bash
   pip install -e ../saraswati-tenant-kit/python
   ```

3. Create the tables and load the sample.

   ```bash
   python scripts/bootstrap.py
   ```

   Running it again does not duplicate the sample. Alembic can create the same empty tables with `alembic upgrade head`. The script is what also inserts the rows Swagger can click through.

4. Start the API on port **8010** so it does not collide with faculty on 8000.

   ```bash
   uvicorn app.main:app --port 8010 --reload
   ```

- Swagger: http://localhost:8010/docs
- OpenAPI: http://localhost:8010/openapi.json
- API base: http://localhost:8010/api/v1
- Health: http://localhost:8010/health

While `APP_ENV=development`, every host (including localhost) is the sample school `11111111-1111-4111-8111-111111111111`. Production leaves school lookup to `platform.tenant_domains` and ignores `DEV_TENANT_ID`.

The database user in docker is a superuser, and a superuser bypasses row-level security even when the policy is forced. The policy is still installed. A restricted role would only see rows for `app.tenant_id`.

## Who calls what

Authorize in Swagger with one bearer token. These three exist only when `APP_ENV=development`. A real JWT is also accepted (`role`, `sub`, `tenant_id`, signed with `SECRET_KEY`). `Admin` means School Admin. `Teacher` means Faculty.

| Token | Role | Can call |
| --- | --- | --- |
| `dev-admin` | School Admin | Platform create and read. Open the year, holidays, generate and edit the syllabus plan. Coverage and teacher alerts. |
| `dev-headmaster` | Headmaster | The same writes as Admin, including coverage and closing an alert. |
| `dev-faculty` | Faculty | Read the plan (`/syllabus-plan`, `/syllabus-plan/mine`, `/syllabus-plan/covered`). `POST /teaching-log` and `POST /lesson-plans/current`. |

A missing or unknown role is 401. A known role on the wrong route is 403. A token whose `tenant_id` is a different school is 401.

`class_id` is a query parameter when a list is being narrowed, and a field in the body when a row is being written. The service never reads `X-Class-Id`.

Lists are `{"items", "total"}`. Dates are ISO. Fields are snake_case.

## What the sample contains

One board, AP SCERT. One calendar for 2026-27 with no `board_id`, recommended by that board. Two blocks, July and August. One Mathematics topic, Real Numbers, that starts in July (`planned`) and continues in August (`continues`). One assessment, FA I, covering July. One active school year. One plan row for class 1, subject 1, at version 1, with an audit row.

Try, in order, with `dev-admin`:

- `GET /api/v1/boards` and `GET /api/v1/calendars` (the calendar body has no board).
- `GET /api/v1/syllabus-items/{item_id}/spans` to see the topic in two blocks.
- `PATCH /api/v1/syllabus-plan/{plan_id}` with `version_no: 1`. The row becomes version 2. Sending version 1 again is 409.
- `GET /api/v1/syllabus-plan/{plan_id}/audit`.

Then with `dev-faculty`:

- `POST /api/v1/teaching-log` for class 1, a date, period 1, status `taught`, and that `plan_id`.
- `POST /api/v1/lesson-plans/current` with `{"class_id": 1, "subject_id": 1}` and no chapter name. It returns Real Numbers until the taught count reaches the planned periods.

Coverage status is `on_track` at 90% or above, `behind` from 70 to 89, and `critical` below 70.

## Corrections from the design notes

- A calendar has no `board_id`. `calendar_block` points at the calendar only. `board_calendar` is the recommendation.
- A lesson is not trapped in one block. `syllabus_item` has no `block_id`. Spans live on `syllabus_item_block` and `syllabus_plan_segment`. A teaching-log date outside the suggested block is slippage, not a bad row.
- Alerts are derived. `missed_days` is counted when the list is read. Only `marking_review` is stored, and only once a streak reaches three working days. There is no teacher-update log and no notification table.
- `class_id` is never a header.
- The syllabus plan has `version_no` and `syllabus_plan_audit`, plus `created_by`, `created_at`, `updated_by`, and `updated_at`.
- Headmaster and Admin write the plan. Other roles only read it.
- `POST /lesson-plans/current` generates a plan for the current topic only.

## Open items

Not built in this pass.

- The actual dashboards. Admin, Headmaster, and teacher screens do not exist here. Each one calls the routes above once it is built.
- Login. [sgs-frontend](../sgs-frontend) does not yet mint a token for this service, and Headmaster has no SSO target today. Until that lands, use the development bearer tokens above.
- Class scope. The same Faculty role means a different authority in each class. That is resolved at login later, in `sgs-frontend` (`auth.ts` and `app/api/sso-token/route.ts`), and carried on the token. This service does not look up class or subject scope, and it does not check the token for either.
- The faculty lesson-planner screen still asks for a chapter. It should call `POST /lesson-plans/current` instead.
- Auto test still picks chapters itself. It should call `GET /syllabus-plan/covered`.
- Class, subject, chapter, and timetable rows are read from the existing school tables (`class_master`, `subject_master`, `chapter_master`, `timetable`). This service does not create them. Without those tables, plan generation needs `class_id` and `subject_id`, chapter suggestions are empty, and teacher alerts are an empty list.
