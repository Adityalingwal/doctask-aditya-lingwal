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
    status: "waiting for review",
    stage: "review",
    skipped: [],
    ended_early_reason: null,
    failure_reason: null,
    decisions: [],
    examine: null,
    cost_and_timing: costAndTimingReply(),
    exported: false,
    ...overrides,
  };
}

export function costAndTimingReply(overrides = {}) {
  return {
    stages: [
      { stage: "ingest", seconds: 0.031 },
      { stage: "extract", seconds: 4.212 },
      { stage: "match", seconds: 1.804 },
      { stage: "examine", seconds: 1.109 },
    ],
    total_seconds: 7.156,
    tokens: {
      prompt: 350,
      completion: 35,
      calls_reporting_usage: 3,
      calls_without_usage: 0,
    },
    estimated_cost_usd: "0.000196",
    estimate_note:
      "An estimate: the tokens the model reported, multiplied by the rates in "
      + "config/model.yaml. It is not a bill.",
    cost_unknown_reason: null,
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
    ...overrides,
  };
}

export function examineReply(overrides = {}) {
  return {
    rules: [
      { id: "R1", text: "Every requirement must have a written scope entry." },
      {
        id: "R3",
        text: "No requirement may sit beyond max_days without movement.",
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
    columns: [
      "what_was_asked",
      "in_writing",
      "what_testing_found",
      "status",
      "blocked_on",
      "first_seen",
      "last_moved",
    ],
    rows: [
      {
        row_number: 1,
        fingerprint: "a1b2c3d4e5f60718",
        cells: {
          what_was_asked: "Applicants upload supporting documents.",
          in_writing: "Yes — 12 March scope, section 2.",
          what_testing_found: "Upload failed for files over 10 MB.",
          status: "Partial",
          blocked_on: "Nothing recorded.",
          first_seen: "2026-03-12",
          last_moved: "2026-03-26",
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
