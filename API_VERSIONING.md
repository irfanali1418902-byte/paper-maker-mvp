# API Versioning Strategy — AII Smart Paper Maker

This document defines how we version the HTTP API, how breaking changes are
handled, and how versions transition through our Railway deployment.

It sits alongside `CLAUDE.md` (§1 URLs: all routes live under `/api/...`,
kebab-case in paths) and `ARCHITECTURE.md` (layering). Nothing here
overrides those — this is about the *version* segment of the URL, not the
layering behind it.

---

## 1. Current state — implicit v1

Every route today is mounted **unversioned** under `/api/...`. This is our
**implicit version 1**: the current contract is frozen as v1, and the
unversioned paths continue to work as permanent aliases for their v1
equivalents (see §4). No client breaks the day we introduce the version
segment.

### Current (v1) endpoints

```
# Questions
POST /api/generate-questions
GET  /api/questions

# Papers
POST /api/generate-paper
POST /api/generate-adaptive-paper
POST /api/paper/{paper_id}/replace-question
GET  /api/paper/{paper_id}
GET  /api/paper/{paper_id}/result-template
POST /api/paper/{paper_id}/upload-results

# Dashboard / analytics
GET  /api/paper/{paper_id}/uploads
GET  /api/paper/{paper_id}/dashboard
GET  /api/upload/{upload_id}/dashboard

# Export
GET  /api/paper/{paper_id}/export.docx
GET  /api/paper/{paper_id}/export.pdf

# Syllabus
GET  /api/syllabus-grades
POST /api/syllabus/upload-pdf
POST /api/syllabus/upload-zip
GET  /api/syllabus-topics

# School settings
GET  /api/school-settings
POST /api/school-settings

# Stats
GET  /api/stats
```

Each of the above is contractually equivalent to its `/api/v1/...` form.

---

## 2. URL versioning approach

We use **URL-path versioning** — the version is a segment right after
`/api`:

```
/api/v1/generate-questions
/api/v2/generate-questions
```

Rationale — why path versioning over the alternatives:

- **Header versioning** (`Accept: application/vnd.aii.v2+json`) is
  invisible in a browser address bar and in `curl` copy-paste. Our users
  are teachers and our own debugging is `curl`-first (`CLAUDE.md` §9), so a
  version you can *see and type* wins.
- **Query-param versioning** (`?version=2`) mixes API contract with request
  data and is easy to drop by accident.
- **Path versioning** is greppable, cache-friendly, and unambiguous in
  logs and Railway metrics.

Conventions:

- Version segment is always `v<integer>` — `v1`, `v2`. No minor/patch in
  the URL; non-breaking additions never change the version (see §3).
- The rest of the path stays kebab-case, exactly as `CLAUDE.md` §1
  requires: `/api/v2/generate-questions`, not `/api/v2/generateQuestions`.
- In FastAPI this is one `APIRouter(prefix="/api/v2")` per version; routers
  are mounted in `app/main.py`. Route handlers and the service/repository
  layers below them are version-agnostic — a version bump lives at the
  routing edge only.

---

## 3. What counts as a breaking change

We bump the major version **only** for breaking changes. A change is
**breaking** if an existing, correct client could stop working:

- Removing an endpoint, or removing/renaming a response field.
- Renaming or removing a request field, or making an optional request field
  required.
- Changing a field's type or the meaning of an existing value.
- Changing an HTTP status code a client is expected to branch on
  (see the `CLAUDE.md` §2 status-code map).
- Changing the semantics of an existing default (e.g. redefining what
  `bloom_distribution: "balanced"` produces).

A change is **non-breaking** and ships **without** a version bump:

- Adding a new endpoint.
- Adding a new *optional* request field with a safe default.
- Adding a new field to a response body (clients must ignore unknown
  fields).
- Adding a new accepted value to an existing enum, where old values keep
  their meaning.
- Bug fixes that bring behavior in line with the documented contract.

When in doubt, treat it as breaking. A false "breaking" costs us a parallel
route for a while; a false "non-breaking" costs a teacher a broken paper
mid-term.

---

## 4. Handling breaking changes

When a breaking change is unavoidable:

1. **Stand up the new version alongside the old.** Add
   `/api/v2/...` routers while `/api/v1/...` (and the unversioned aliases)
   keep serving the old contract unchanged. Both run in the same
   deployment.
2. **Share the layer below the route.** Only the route/serialization edge
   forks per version; services and repositories stay single-sourced. If a
   service genuinely must diverge, that's a signal to design the change to
   be additive instead.
3. **Migrate the frontend** (`static/`) to v2 explicitly, so we control
   exactly when our own client moves.
4. **Announce the deprecation** of v1 (see §5) the moment v2 ships — never
   retroactively.

The unversioned `/api/...` paths remain permanent aliases of **v1**. They
are never silently re-pointed at v2 — repointing them would break every
existing client at once, which is the exact failure this whole strategy
exists to prevent.

---

## 5. Deprecation policy

- **Announce on release.** When vN+1 ships, vN is marked deprecated the
  same day, in this file and in the release notes.
- **Minimum support window: one full academic term** (a KPK school term,
  ~4–5 months) after the deprecation announcement. We never retire a
  version mid-term, because a teacher's exam cycle spans a term and a
  broken endpoint mid-session is unacceptable.
- **Signal deprecation in the response.** Deprecated-version responses
  carry a `Deprecation: true` header and a `Sunset: <RFC-1123 date>` header
  giving the removal date, plus a `Warning` header pointing at the
  successor version. Clients and our own logs can then see the clock
  ticking.
- **Removal.** After the sunset date passes and metrics confirm traffic to
  the old version has effectively stopped, the vN routers are removed in a
  single, clearly-messaged commit. If traffic hasn't dropped, we extend
  rather than break users.
- **v1 unversioned aliases are exempt** from removal — they are a permanent
  compatibility surface, not a deprecated version.

---

## 6. Railway deployment and version transitions

We deploy on Railway as a single FastAPI service, so version transitions
are handled **in-app**, not via separate services:

- **Both versions live in one deployment.** Because vN and vN+1 are just
  different routers mounted in the same `app.main:app`, a single Railway
  deploy serves every supported version at once. There is no separate
  service, database, or domain per version.
- **Atomic, health-checked rollout.** Railway builds the new image and
  swaps to it only after the health check passes, then drains the old
  container. Because the new image already contains *both* v1 and v2
  routes, no client sees a window where its version is missing. If the
  health check fails, Railway keeps the previous deploy live and no version
  disappears.
- **Instant rollback.** If a deploy that removes a deprecated version
  causes problems, we redeploy the previous Railway build to restore it
  immediately — the removal is reversible until we're confident.
- **One database across versions.** Since all versions share the single
  SQLite database, schema changes must stay backward-compatible for as long
  as any served version depends on the old shape. Migrations follow
  `CLAUDE.md` §5 (idempotent `ALTER TABLE ... ADD COLUMN`); we add columns,
  we don't drop or repurpose them while an older API version still reads
  them.
- **Env / secrets are shared.** Provider keys and config are read once at
  their owning module (`CLAUDE.md` §6) and are not versioned; a new API
  version reuses the same Railway environment variables.

---

## 7. Summary

| Concern | Decision |
|---|---|
| Scheme | URL-path versioning: `/api/v1/...`, `/api/v2/...` |
| Current version | v1 (unversioned `/api/...` = permanent v1 alias) |
| Granularity | Major integer only; non-breaking changes never bump it |
| Breaking change | New version alongside old; old contract untouched |
| Deprecation window | ≥ one KPK academic term after announcement |
| Deprecation signal | `Deprecation` / `Sunset` / `Warning` headers |
| Deployment | Single Railway service serving all live versions |
| Database | One shared DB; migrations stay backward-compatible |
