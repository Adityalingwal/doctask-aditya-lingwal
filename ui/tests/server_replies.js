// The shapes these builders return are the shapes the API actually returns:
// `app/runs/run_status.py` for a run, `app/register/export_register.py` for an
// export, and `app/refusal.py` carried as `{"detail": ...}` by
// `app/api/routes.py`. A test that invented its own shape would prove only
// that the component renders its own props.

export const runId = "0f3f0f6a-4f8a-4a4a-9c1e-3f6b2d5a7c11";
export const projectId = "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d";

export function runReply(overrides = {}) {
  return {
    run_id: runId,
    project_id: projectId,
    status: "needs review",
    stage: "review",
    skipped: [],
    reported_instructions: [],
    ended_early_reason: null,
    failure_reason: null,
    decisions: [],
    examine: null,
    finished_stages: ["ingest", "extract", "match", "examine"],
    exported: false,
    ...overrides,
  };
}

export function decisionReply(overrides = {}) {
  return {
    decision_id: "2c4e6a80-1111-4b22-8333-444455556666",
    kind: "possible match",
    question:
      "Is 'Applicants upload documents' the same requirement as row 2, "
      + "'Applicant document upload'?",
    outcome: null,
    // Only a "finding" decision carries these; every other kind sends null,
    // the same honesty rule the server itself follows.
    rule_text: null,
    issue: null,
    evidence: null,
    // The register row this decision is about — a finding's row, or the row a
    // match would attach to. The export gate is about no single row and sends
    // null. `moved_cells` is what an approved observation match would write,
    // read back from the move Commit itself applies.
    row_number: 2,
    moved_cells: [],
    ...overrides,
  };
}

// A finding decision (screen 4): the rule's own words, the row and what it
// did to break the rule, and the evidence — never a rule code.
export function findingDecisionReply(overrides = {}) {
  return decisionReply({
    decision_id: "7a1b2c3d-4444-4e55-8666-777788889999",
    kind: "finding",
    question:
      "Anything built must have a written requirement; a verbal mention is "
      + "not enough. Row #4 — SMS reminders before an appointment — was "
      + "asked for in the meeting, but no written requirement names it. "
      + "Attach this finding to row #4?",
    rule_text:
      "Anything built must have a written requirement; a verbal mention is "
      + "not enough.",
    row_number: 4,
    issue:
      "WhatsApp notification was asked for in the meeting but no written "
      + "requirement names it.",
    evidence: "\"same notification sent over WhatsApp\" — meeting-notes-10-mar.md",
    ...overrides,
  });
}

export function examineReply(overrides = {}) {
  return {
    rules: [
      { id: "R1", text: "Every requirement must have a written scope entry." },
      {
        id: "R3",
        text: "No requirement may sit beyond max_days days without movement.",
        params: { max_days: 14 },
      },
    ],
    rows_examined: 5,
    findings: [],
    ...overrides,
  };
}

export function exportReply(overrides = {}) {
  return {
    project: { id: projectId, name: "Acme intake portal" },
    run_id: runId,
    exported_at: "2026-03-26T10:00:00+00:00",
    columns: ["what_was_asked", "in_writing", "what_testing_found", "status"],
    rows: [
      {
        row_number: 1,
        fingerprint: "a1b2c3d4e5f60718",
        cells: {
          what_was_asked: "Applicants upload supporting documents.",
          in_writing: "Yes — 12 March scope, section 2.",
          what_testing_found: "Upload failed for files over 10 MB.",
          status: "Partial",
        },
        citations: [
          {
            cell: "what_was_asked",
            source_file: "12-march-scope.md",
            place: "Section 2 — Applicant portal",
            source_words: "applicants must be able to upload supporting documents",
            absence_statement: null,
          },
          {
            cell: "status",
            source_file: "26-march-scope.md",
            place: null,
            source_words: null,
            absence_statement:
              "the 26 March scope was read in full and no longer asks for "
              + "supporting document upload.",
          },
        ],
        findings: [],
      },
    ],
    examine: {
      rules: [
        { id: "R1", text: "Every requirement must have a written scope entry." },
      ],
      rows_examined: 1,
      findings: [],
    },
    ...overrides,
  };
}

// One project, its one run matching runReply()'s defaults so a test that
// opens `runId` through the run door sees the same run listed here.
export function projectReply(overrides = {}) {
  return {
    project_id: projectId,
    name: "Acme intake portal",
    source_folder_path: "sample-projects/intake-portal",
    run_count: 1,
    most_recent_run_at: "2026-03-26T10:00:00+00:00",
    runs: [
      {
        run_id: runId,
        run_number: 1,
        status: "needs review",
        stage: "review",
        started_at: "2026-03-26T10:00:00+00:00",
        waiting_decisions: 0,
        finished_stages: ["ingest", "extract", "match", "examine"],
        row_count: null,
      },
    ],
    ...overrides,
  };
}

// `GET /projects` (L1): every test renders against this unconditional read,
// whether or not the test cares what it says.
export function projectsReply(overrides = {}) {
  return {
    projects: [projectReply()],
    projects_root: "sample-projects",
    available_folders: [
      "sample-projects/intake-portal",
      "sample-projects/northside-dental",
    ],
    ...overrides,
  };
}

// One fake server, routed by method and path exactly as FastAPI routes it, so
// a request the application does not serve fails the test loudly.
export function serverAnswering(routes) {
  const calls = [];
  const answer = async (requested, options = {}) => {
    const method = (options.method ?? "GET").toUpperCase();
    const path = new URL(requested, "http://localhost:8000").pathname;
    calls.push({ method, path, body: options.body });
    const route = routes.find(
      (candidate) => candidate.method === method && candidate.path === path,
    );
    if (route === undefined) {
      throw new Error(`the application requested ${method} ${path}, which this run's server does not serve`);
    }
    const reply = typeof route.reply === "function" ? route.reply() : route.reply;
    const status = reply.status ?? 200;
    return {
      ok: status < 400,
      status,
      json: async () => reply.body,
    };
  };
  answer.calls = calls;
  return answer;
}
