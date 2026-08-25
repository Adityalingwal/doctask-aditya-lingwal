// The shapes these builders return are the shapes the API actually returns:
// `app/runs/run_status.py` for a run, `app/register/export_register.py` for
// the register document, and `app/refusal.py` carried as `{"detail": ...}` by
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
    // What the adding press would write, and how many questions still stand
    // between the person and pressing it. A run that has ended answers null:
    // the block previews a press, it does not record one.
    add_will_write: [],
    open_decisions: 0,
    examine: null,
    finished_stages: ["ingest", "extract", "match", "examine"],
    exported: false,
    ...overrides,
  };
}

// The whole text and the parts it was taken apart into, both written out
// literally rather than one built from the other: a fixture that assembled
// the text from the parts would let the screen's own joining pass its own
// test. `tests/register/test_review_question_wording.py` is the canonical
// form these follow.
const ROW_TWO_CELLS = {
  "What was asked": "Applicants upload supporting documents.",
  "Written down": "Not known yet",
  "What testing found": "Not known yet",
  Status: "Requested",
};

export function decisionReply(overrides = {}) {
  return {
    decision_id: "2c4e6a80-1111-4b22-8333-444455556666",
    kind: "possible match",
    question:
      "Register row 2\n"
      + "What was asked: Applicants upload supporting documents.\n"
      + "Written down: Not known yet\n"
      + "What testing found: Not known yet\n"
      + "Status: Requested\n"
      + "\n"
      + '26-march-scope.md, under "Applicant portal", says:\n'
      + '"applicants must be able to upload supporting documents"\n'
      + "\n"
      + "Is this the same ask as row 2?\n"
      + "\n"
      + "Approve → Row 2 changes: Written down: Yes\n"
      + "Reject → A new row is created for this ask, with Written down: Yes.",
    outcome: null,
    // Only a "finding" decision carries these; every other kind sends null,
    // the same honesty rule the server itself follows.
    rule_text: null,
    issue: null,
    evidence: null,
    // The register row this decision is about — a finding's row, or the row a
    // match would attach to. The export gate is about no single row and sends
    // null. `if_approved` is what approving would write, read back from the
    // move Commit itself applies; `row` and `quotes` are the parts the whole
    // `question` text above was built from.
    row_number: 2,
    row: { row_number: 2, label: "Register row 2", cells: ROW_TWO_CELLS },
    quotes: [
      {
        source_line: '26-march-scope.md, under "Applicant portal"',
        quote: "applicants must be able to upload supporting documents",
      },
    ],
    if_approved: [{ cell: "Written down", value: "Yes" }],
    if_rejected: "A new row is created for this ask, with Written down: Yes.",
    ...overrides,
  };
}

// Two observations about one row are one decision carrying two quote blocks
// under one question (item 42), and the approve line names only the cells
// Commit will actually write.
export function observationMatchReply(overrides = {}) {
  return decisionReply({
    decision_id: "3d5f7b91-2222-4c33-8444-555566667777",
    kind: "observation match",
    question:
      "Register row 2\n"
      + "What was asked: Applicants upload supporting documents.\n"
      + "Written down: Yes\n"
      + "What testing found: Not known yet\n"
      + "Status: Requested\n"
      + "\n"
      + 'testing-feedback-25-mar.md, under "What we found", says:\n'
      + '"the reminder goes out a day early"\n'
      + "\n"
      + 'testing-feedback-25-mar.md, under "What we found", says:\n'
      + '"upload failed for files over 10 MB"\n'
      + "\n"
      + "Is this about row 2?\n"
      + "\n"
      + "Approve → Row 2 changes: What testing found: the reminder goes out a "
      + "day early  Status: Partial\n"
      + "Reject → Row 2 stays as it is.",
    row: {
      row_number: 2,
      label: "Register row 2",
      cells: { ...ROW_TWO_CELLS, "Written down": "Yes" },
    },
    quotes: [
      {
        source_line: 'testing-feedback-25-mar.md, under "What we found"',
        quote: "the reminder goes out a day early",
      },
      {
        source_line: 'testing-feedback-25-mar.md, under "What we found"',
        quote: "upload failed for files over 10 MB",
      },
    ],
    if_approved: [
      { cell: "What testing found", value: "the reminder goes out a day early" },
      { cell: "Status", value: "Partial" },
    ],
    if_rejected: "Row 2 stays as it is.",
    ...overrides,
  });
}

// A finding decision (screen 4): the rule's own words and the model's issue
// line, wrapped by the backend — never a rule code, and no quote block at all.
export function findingDecisionReply(overrides = {}) {
  return decisionReply({
    decision_id: "7a1b2c3d-4444-4e55-8666-777788889999",
    kind: "finding",
    question:
      "Register row 4\n"
      + "What was asked: SMS reminders before an appointment.\n"
      + "Written down: Not mentioned\n"
      + "What testing found: Not known yet\n"
      + "Status: Requested\n"
      + "\n"
      + "Rule: Anything built must have a written requirement; a verbal "
      + "mention is not enough.\n"
      + "\n"
      + "26-march-scope.md was read, and it says nothing about this "
      + "requirement.\n"
      + "\n"
      + "Does row 4 break this rule?\n"
      + "\n"
      + "Approve → The finding is added to row 4.\n"
      + "Reject → The finding is not added.",
    rule_text:
      "Anything built must have a written requirement; a verbal mention is "
      + "not enough.",
    row_number: 4,
    row: {
      row_number: 4,
      label: "Register row 4",
      cells: {
        "What was asked": "SMS reminders before an appointment.",
        "Written down": "Not mentioned",
        "What testing found": "Not known yet",
        Status: "Requested",
      },
    },
    issue:
      "26-march-scope.md was read, and it says nothing about this requirement.",
    evidence: "Not mentioned",
    quotes: [],
    if_approved: [],
    if_rejected: "The finding is not added.",
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

export function registerReply(overrides = {}) {
  return {
    project: { id: projectId, name: "Acme intake portal" },
    exported_at: "2026-03-26T10:00:00+00:00",
    columns: ["what_was_asked", "in_writing", "what_testing_found", "status"],
    rows: [
      {
        row_number: 1,
        fingerprint: "a1b2c3d4e5f60718",
        cells: {
          what_was_asked: "Applicants upload supporting documents.",
          in_writing: "Not mentioned",
          what_testing_found: "Upload failed for files over 10 MB.",
          status: "Partial",
        },
        // One entry per thing a document said, and the cells it supports.
        evidence: [
          {
            source_line: '12-march-scope.md, under "Section 2 — Applicant portal"',
            quote: "applicants must be able to upload supporting documents",
            absence: null,
            cells: ["What was asked"],
          },
          {
            source_line: null,
            quote: null,
            absence:
              "26-march-scope.md was read, and it does not mention this ask.",
            cells: ["Written down"],
          },
        ],
        // A clean row carries no findings key at all (item 43) — the fixture
        // models the register JSON exactly as the backend builds it.
      },
    ],
    rules: {
      run_number: 2,
      rows_examined: 1,
      rules: [
        { id: "R1", text: "Every requirement must have a written scope entry." },
      ],
    },
    ...overrides,
  };
}

// One finding as `app/examine/read_findings.py`'s `finding_on_the_register`
// answers with it: keyed on its own id, and naming the run that raised it.
// The key is absent from a row nothing was found wrong with, which is why no
// fixture row carries an empty list.
export function findingOnTheRegister(overrides = {}) {
  return {
    finding_id: "5f6e7d8c-9999-4aaa-8bbb-cccccccccccc",
    raised_by_run: 2,
    row_number: 1,
    rule_id: "R1",
    rule_text: "Every requirement must have a written scope entry.",
    issue:
      "26-march-scope.md was read, and it says nothing about this "
      + "requirement.",
    evidence: "Not mentioned",
    question: "Does row 1 break this rule?",
    ...overrides,
  };
}

// `GET /projects/{id}/history` (app/register/read_history.py): the three entry
// shapes the core function folds the audit trail into, newest first. A row's
// birth arrives already folded into one `row created` entry, so no test here
// has to reproduce the four cell writes that stand behind it.
export function historyReply(overrides = {}) {
  return {
    entries: [
      {
        kind: "cell change",
        row_number: 1,
        cell: "status",
        old_value: "Requested",
        new_value: "Done",
        changed_at: "2026-03-27T09:30:00+00:00",
        run_number: 2,
        source_file: "testing-feedback-25-mar.md",
      },
      {
        kind: "cell change",
        row_number: 1,
        cell: "in_writing",
        old_value: "Not mentioned",
        new_value: "Yes",
        changed_at: "2026-03-27T09:30:00+00:00",
        run_number: 2,
        source_file: "26-march-scope.md",
      },
      {
        kind: "finding attached",
        row_number: 1,
        // `app/register/commit_register.py` writes the rule's own words after
        // one word of its own — never a rule id (item 48).
        detail: "Finding: Every requirement must have a written scope entry.",
        changed_at: "2026-03-27T09:30:00+00:00",
        run_number: 2,
      },
      {
        kind: "row created",
        row_number: 1,
        what_was_asked: "Applicants upload supporting documents.",
        changed_at: "2026-03-26T10:00:00+00:00",
        run_number: 1,
        source_file: "meeting-notes-10-mar.md",
      },
    ],
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
    // Whether each of those folders holds a file the system could read: an
    // empty folder makes a project and starts no run (locked change (a)).
    has_files_by_folder: {
      "sample-projects/intake-portal": true,
      "sample-projects/northside-dental": true,
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
