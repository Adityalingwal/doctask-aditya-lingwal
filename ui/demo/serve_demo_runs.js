// The screen is designed against states, not one screenshot: a run mid-extract,
// a failed run, a review with gates waiting, an exported register, and the
// rules-only route that never runs Extract or Match. None of them can be seen
// without the application, so the Vite dev server answers them here.
//
// The shapes come from `../tests/server_replies.js`, which follows the API
// itself. Inventing a second set of fake bodies here would let the screen drift
// from what the application actually returns.
//
// `apply: "serve"` keeps every line of this out of `vite build`, so no demo run
// can reach the bundle FastAPI serves.
import {
  decisionReply,
  examineReply,
  exportReply,
  runReply,
} from "../tests/server_replies.js";

const JSON_HEADER = { "Content-Type": "application/json" };

function demoRuns() {
  return {
    "demo-review": {
      run: runReply({
        run_id: "demo-review",
        status: "waiting for review",
        stage: "review",
        decisions: [
          decisionReply({
            decision_id: "demo-decision-1",
            kind: "possible match",
            question:
              "Is 'Applicants upload documents' the same requirement as row 2, "
              + "'Applicant document upload'?",
          }),
          decisionReply({
            decision_id: "demo-decision-2",
            kind: "rule finding",
            question:
              "R1 — row 4 'SMS reminders before an appointment' has no written "
              + "scope entry. Attach this finding to that row?",
          }),
          decisionReply({
            decision_id: "demo-decision-3",
            kind: "withdrawal",
            question:
              "The 26 March scope was read in full and no longer asks for "
              + "supporting document upload. Withdraw row 1?",
          }),
          decisionReply({
            decision_id: "demo-decision-4",
            kind: "export",
            question: "Export this register with 7 rows and 1 approved finding?",
          }),
        ],
        examine: examineReply({
          rows_examined: 7,
          findings: [
            {
              row_number: 4,
              rule_id: "R1",
              issue: "no written scope entry supports this requirement",
              evidence: "meeting-notes-20-mar.md is the only source",
            },
          ],
        }),
        finished_stages: ["ingest", "extract", "match", "examine"],
      }),
    },

    // Only the rules changed, so Ingest routed straight to Examine (D03/D07):
    // Extract and Match never ran on this one and never will.
    "demo-running": {
      run: runReply({
        run_id: "demo-running",
        status: "running",
        stage: "examine",
        decisions: [],
        examine: null,
        finished_stages: ["ingest"],
      }),
    },

    "demo-failed": {
      run: runReply({
        run_id: "demo-failed",
        status: "failed",
        stage: "extract",
        decisions: [],
        examine: null,
        failure_reason:
          "OPENROUTER_API_KEY is empty — copy .env.example to .env and put an "
          + "OpenRouter API key in it, then start the run again.",
        skipped: [
          {
            source_file: "northside-dental-brochure.pdf",
            reason: "read as an unrelated document, so it produced no requirement",
          },
          {
            source_file: "old-contract-scan.pdf",
            reason:
              "the file is a scanned image with no extractable text — export it "
              + "as a text PDF, or supply the wording as .md, and run again",
          },
          {
            source_file: "12-march-scope.docx",
            quote_not_found: "patients should be able to reschedule without calling",
            reason:
              "the quoted words were not found in the extracted text, so no "
              + "citation could be written for them",
          },
        ],
        finished_stages: ["ingest"],
      }),
    },

    "demo-exported": {
      run: runReply({
        run_id: "demo-exported",
        status: "done",
        stage: "commit",
        exported: true,
        decisions: [
          decisionReply({
            decision_id: "demo-exported-decision-1",
            kind: "export",
            question: "Export this register with 4 rows and 1 approved finding?",
            outcome: "approved",
          }),
        ],
        examine: examineReply({ rows_examined: 4 }),
        finished_stages: [
          "ingest",
          "extract",
          "match",
          "examine",
          "review",
          "commit",
        ],
      }),
      export: exportedRegister(),
    },
  };
}

function exportedRegister() {
  const base = exportReply();
  return {
    ...base,
    run_id: "demo-exported",
    project: { id: base.project.id, name: "Northside Dental" },
    rows: [
      base.rows[0],
      {
        row_number: 2,
        fingerprint: "b2c3d4e5f6071829",
        cells: {
          what_was_asked: "Patients book an appointment online.",
          in_writing: "Yes — 12 March scope, section 1.",
          what_testing_found: "Booking works on desktop and mobile.",
          status: "Done",
          blocked_on: "Nothing recorded.",
          first_seen: "2026-03-12",
          last_moved: "2026-03-24",
        },
        citations: [
          {
            cell: "what_was_asked",
            source_file: "12-march-scope.docx",
            place: "line 14",
            source_words: "patients should be able to book an appointment online",
            absence_statement: null,
          },
          {
            cell: "what_testing_found",
            source_file: "testing-feedback-24-mar.pdf",
            place: "page 2",
            source_words: "booking confirmed on both desktop and mobile",
            absence_statement: null,
          },
        ],
        findings: [],
      },
      {
        row_number: 3,
        fingerprint: "c3d4e5f607182930",
        cells: {
          what_was_asked: "Staff see the day's appointments on one screen.",
          in_writing: "Yes — 12 March scope, section 3.",
          what_testing_found: "No evidence yet.",
          status: "Blocked",
          blocked_on: "The practice has not supplied its staff rota format.",
          first_seen: "2026-03-12",
          last_moved: "2026-03-20",
        },
        citations: [
          {
            cell: "blocked_on",
            source_file: "meeting-notes-20-mar.md",
            place: "Blockers",
            source_words: "we still do not have the rota format from the practice",
            absence_statement: null,
          },
        ],
        findings: [],
      },
      {
        row_number: 4,
        fingerprint: "d4e5f60718293041",
        cells: {
          what_was_asked: "Patients get an SMS reminder before an appointment.",
          in_writing: "No written scope entry.",
          what_testing_found: "No evidence yet.",
          status: "No evidence yet",
          blocked_on: "Nothing recorded.",
          first_seen: "2026-03-20",
          last_moved: "2026-03-20",
        },
        citations: [
          {
            cell: "what_was_asked",
            source_file: "meeting-notes-20-mar.md",
            place: "Asks",
            source_words: "they also want a text message before the appointment",
            absence_statement: null,
          },
        ],
        findings: [
          {
            row_number: 4,
            rule_id: "R1",
            issue: "no written scope entry supports this requirement",
            evidence: "meeting-notes-20-mar.md is the only source",
          },
        ],
      },
    ],
    examine: examineReply({
      rows_examined: 4,
      findings: [
        {
          row_number: 4,
          rule_id: "R1",
          issue: "no written scope entry supports this requirement",
          evidence: "meeting-notes-20-mar.md is the only source",
        },
      ],
    }),
  };
}

/**
 * Vite middleware answering the endpoints the screen calls, for demo runs
 * only. An unknown run id is refused the way the application refuses one.
 */
export default function serveDemoRuns() {
  // Held per dev-server start, so an answered gate stays answered while the
  // screen polls, and a restart puts every demo run back where it began.
  const runs = demoRuns();

  return {
    name: "serve-demo-runs",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use(async (request, response, next) => {
        const url = new URL(request.url, "http://localhost");
        const parts = url.pathname.split("/").filter(Boolean);
        // The index lives here rather than in the screen, so removing this
        // folder and its one line of `vite.config.js` removes every trace of
        // the demo without touching a single file under `src/`.
        if (parts[0] === "demo" && parts.length === 1) {
          respondWithIndex(response, Object.keys(runs));
          return;
        }
        if (parts[0] !== "runs") {
          next();
          return;
        }
        if (request.method === "GET" && parts.length === 1) {
          // Newest first, the order the application itself answers in — a demo
          // that listed them in any other order would not be showing the screen
          // what it will really be given.
          reply(response, 200, {
            runs: Object.values(runs)
              .map(runListEntry)
              .sort((one, other) => other.started_at.localeCompare(one.started_at)),
          });
          return;
        }
        const demoRun = runs[parts[1]];
        if (demoRun === undefined) {
          reply(response, 404, {
            detail:
              `No run ${parts[1]} exists. The dev server answers only the demo `
              + `runs: ${Object.keys(runs).join(", ")}.`,
          });
          return;
        }
        if (request.method === "GET" && parts.length === 2) {
          reply(response, 200, demoRun.run);
          return;
        }
        if (request.method === "GET" && parts[2] === "export") {
          if (demoRun.export === undefined) {
            reply(response, 409, {
              detail:
                "This run has not exported a register. Approve its export "
                + "decision and finish the review first.",
            });
            return;
          }
          reply(response, 200, demoRun.export);
          return;
        }
        if (request.method === "POST" && parts[2] === "decisions") {
          const sent = JSON.parse(await bodyOf(request));
          const decision = demoRun.run.decisions.find(
            (candidate) => candidate.decision_id === sent.decision_id,
          );
          if (decision === undefined) {
            reply(response, 404, {
              detail: `No decision ${sent.decision_id} belongs to this run.`,
            });
            return;
          }
          decision.outcome = sent.outcome;
          reply(response, 200, { decision_id: sent.decision_id, outcome: sent.outcome });
          return;
        }
        if (request.method === "POST" && parts[2] === "finish-review") {
          const unanswered = demoRun.run.decisions.filter(
            (candidate) => candidate.outcome === null,
          );
          if (unanswered.length > 0) {
            reply(response, 409, {
              detail:
                `${unanswered.length} decision(s) on this run are unanswered. `
                + "Answer every one of them, then finish the review again.",
            });
            return;
          }
          demoRun.run.status = "done";
          demoRun.run.stage = "commit";
          // A run that finished its review finished Review and Commit with it.
          // Without these the stage strip reads "never ran" and "not started"
          // on a run the same reply calls done.
          demoRun.run.finished_stages = [
            ...demoRun.run.finished_stages,
            "review",
            "commit",
          ];
          reply(response, 200, { run_id: demoRun.run.run_id, status: "done" });
          return;
        }
        next();
      });
    },
  };
}

// One entry of the run list the column reads. Every field is one the run
// itself already carries, so nothing here is a shape the application could not
// answer with once `GET /runs` exists.
const DEMO_PROJECT_NAMES = {
  "demo-review": "Acme intake portal",
  "demo-running": "Northside Dental",
  "demo-failed": "Northside Dental",
  "demo-exported": "Northside Dental",
};

const DEMO_START_TIMES = {
  "demo-review": "2026-08-14T20:41:00+00:00",
  "demo-running": "2026-08-14T20:58:00+00:00",
  "demo-failed": "2026-08-14T18:03:00+00:00",
  "demo-exported": "2026-08-12T09:30:00+00:00",
};

function runListEntry(demoRun) {
  const run = demoRun.run;
  return {
    run_id: run.run_id,
    project_name: DEMO_PROJECT_NAMES[run.run_id],
    status: run.status,
    started_at: DEMO_START_TIMES[run.run_id],
    waiting_decisions: run.decisions.filter(
      (decision) => decision.outcome === null,
    ).length,
    finished_stages: run.finished_stages,
  };
}

const RUN_DESCRIPTIONS = {
  "demo-review": "At review with four gates waiting — the accent, the counter and Finish review",
  "demo-running": "Working, on the rules-only route: Extract and Match never ran",
  "demo-failed": "Failed inside Extract, with three documents skipped for three different reasons",
  "demo-exported": "Done and exported: the full register, its evidence and one finding",
};

function respondWithIndex(response, runIds) {
  const links = runIds
    .map(
      (id) =>
        `<li><a href="/ui/?run=${id}"><code>${id}</code>`
        + `<span>${RUN_DESCRIPTIONS[id] ?? ""}</span></a></li>`,
    )
    .join("");
  response.statusCode = 200;
  response.setHeader("Content-Type", "text/html; charset=utf-8");
  response.end(
    `<!doctype html><html lang="en"><head><meta charset="utf-8">`
    + `<title>Demo runs</title><style>`
    + `body{background:#f6f5f1;color:#0f0f0e;font:14px/1.5 ui-sans-serif,system-ui;`
    + `margin:0;padding:3rem 1.5rem;display:flex;justify-content:center}`
    + `main{width:100%;max-width:44rem}`
    + `h1{font:600 12px/1 ui-monospace,monospace;letter-spacing:.2em;`
    + `text-transform:uppercase;color:#6b6b63;margin:0 0 1.5rem}`
    + `ul{list-style:none;margin:0;padding:0;display:grid;gap:.75rem}`
    + `a{display:block;background:#fff;border:1px solid #0f0f0e;padding:.75rem 1rem;`
    + `text-decoration:none;color:inherit;box-shadow:2px 2px 0 0 #0f0f0e}`
    + `a:hover{background:#cbf74a}`
    + `code{font:600 13px ui-monospace,monospace}`
    + `a code{display:block}`
    + `span{color:#6b6b63;font-size:13px}`
    + `p{color:#6b6b63;margin:1.5rem 0 0}`
    + `</style></head><body><main><h1>Demo runs · dev server only</h1>`
    + `<ul>${links}</ul>`
    + `<p>These runs are served by <code>ui/demo/</code> and never reach a build.</p>`
    + `</main></body></html>`,
  );
}

function reply(response, status, body) {
  response.statusCode = status;
  response.setHeader("Content-Type", JSON_HEADER["Content-Type"]);
  response.end(JSON.stringify(body));
}

async function bodyOf(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf-8");
}
