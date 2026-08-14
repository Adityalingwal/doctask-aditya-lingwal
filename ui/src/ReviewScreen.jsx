import { useCallback, useEffect, useState } from "react";

import Question from "./Question.jsx";
import Register, { Examine } from "./Register.jsx";
import RunList from "./RunList.jsx";
import Section, { WaitingCount } from "./Section.jsx";
import Stages from "./Stages.jsx";
import screenConfig from "../config/screen.json";
import {
  answerDecision,
  finishReview,
  readExport,
  readRun,
  readRuns,
} from "./run_requests.js";

// The one status in which the server accepts an answer or a finished review.
const WAITING_FOR_REVIEW = "waiting for review";

// The screen's own name. The register it shows keeps the name the decisions and
// the exports give it; this is only what the person looking at it calls the
// thing, and it lives in one place so it can be changed in one place.
const PRODUCT_NAME = "Throughline";

export default function ReviewScreen({ runId: openedRunId }) {
  const [runId, setRunId] = useState(openedRunId ?? "");
  const [run, setRun] = useState(null);
  const [exported, setExported] = useState(null);
  // Two refusals, because they stop being true at different moments: a refused
  // read is answered by the next read that succeeds, while a refused answer
  // stands until another answer is sent. One shared value would either leave a
  // dead refusal beside confirmed data, or wipe a live one on the next poll.
  const [readRefusal, setReadRefusal] = useState(null);
  const [answerRefusal, setAnswerRefusal] = useState(null);
  const [answering, setAnswering] = useState(false);
  // The run list is its own read with its own refusal: an application that
  // cannot list runs can still answer perfectly well for the run being
  // reviewed, and one refusal standing in for both would hide that.
  const [runs, setRuns] = useState([]);
  const [runsRefusal, setRunsRefusal] = useState(null);
  const [openSection, setOpenSection] = useState("stages");

  const readListFromServer = useCallback(async () => {
    const answered = await readRuns();
    setRuns(answered.ok ? answered.body.runs : []);
    setRunsRefusal(answered.ok ? null : answered.refusal);
  }, []);

  // A link to one run stays a link a reviewer can keep, so opening a run from
  // the list writes it into the address without adding a history entry.
  const openRun = useCallback((chosen) => {
    setRunId(chosen);
    window.history.replaceState(null, "", `/ui/?run=${encodeURIComponent(chosen)}`);
  }, []);

  const readFromServer = useCallback(async () => {
    if (runId === "") {
      return;
    }
    const answered = await readRun(runId);
    if (!answered.ok) {
      setRun(null);
      setExported(null);
      setReadRefusal(answered.refusal);
      return;
    }
    setRun(answered.body);
    setReadRefusal(null);
    if (!answered.body.exported) {
      setExported(null);
      return;
    }
    const register = await readExport(runId);
    setExported(register.ok ? register.body : null);
    if (!register.ok) {
      setReadRefusal(register.refusal);
    }
  }, [runId]);

  useEffect(() => {
    readFromServer();
    readListFromServer();
    const polling = setInterval(() => {
      readFromServer();
      readListFromServer();
    }, screenConfig.poll_interval_ms);
    return () => clearInterval(polling);
  }, [readFromServer, readListFromServer]);

  // Nothing the person clicked reaches the screen: the answer is sent, and what
  // is shown next is read back from the server that recorded it.
  const answer = useCallback(
    async (decisionId, outcome) => {
      setAnswering(true);
      const answered = await answerDecision(runId, decisionId, outcome);
      setAnswerRefusal(answered.ok ? null : answered.refusal);
      await readFromServer();
      setAnswering(false);
    },
    [runId, readFromServer],
  );

  const finish = useCallback(async () => {
    setAnswering(true);
    const finished = await finishReview(runId);
    setAnswerRefusal(finished.ok ? null : finished.refusal);
    await readFromServer();
    setAnswering(false);
  }, [runId, readFromServer]);

  const waiting =
    run === null
      ? 0
      : run.decisions.filter((decision) => decision.outcome === null).length;

  const openProjectName =
    runs.find((listed) => listed.run_id === runId)?.project_name ?? null;

  // The five sections and their order are fixed; what changes here is that one
  // is read at a time, so a register of forty rows never buries the timings
  // under it.
  const sections =
    run === null
      ? []
      : [
          {
            id: "stages",
            number: "01",
            name: "Stages",
            tab: "Stages",
            body: <Stages run={run} />,
          },
          {
            id: "skipped",
            number: "02",
            name: "Skipped",
            tab: "Skipped",
            tabCount: run.skipped.length === 0 ? null : String(run.skipped.length),
            count: `${run.skipped.length} skipped`,
            body: <Skipped skipped={run.skipped} />,
          },
          {
            id: "decisions",
            number: "03",
            name: "Needs your decision",
            tab: "Decisions",
            tabCount: waiting === 0 ? null : String(waiting),
            tabWaiting: waiting > 0,
            count: <WaitingCount waiting={waiting} />,
            body: (
              <Decisions
                decisions={run.decisions}
                examine={run.examine}
                reviewing={run.status === WAITING_FOR_REVIEW}
                answering={answering}
                waiting={waiting}
                onAnswer={answer}
                onFinish={finish}
              />
            ),
          },
          {
            id: "register",
            number: "04",
            name: "Register",
            tab: "Register",
            tabCount: exported === null ? null : String(exported.rows.length),
            count:
              exported === null ? "not exported" : `${exported.rows.length} rows`,
            body: <RegisterSection exported={exported} />,
          },
          {
            id: "cost",
            number: "05",
            name: "Cost and timing",
            tab: "Cost and timing",
            count: "estimate, not a bill",
            body: <CostAndTiming reported={run.cost_and_timing} />,
          },
        ];

  return (
    // The whole viewport, once. The bar keeps its height, and the two panes
    // below it scroll independently — a long register must never push the run
    // list off the screen.
    <div className="grid h-screen grid-rows-[3.5rem_1fr] overflow-hidden">
      <header className="flex items-center gap-3 bg-ink px-5 text-paper">
        <span className="block h-3 w-3 bg-signal" aria-hidden="true" />
        <h1 className="m-0 font-mono text-sm font-semibold tracking-tight">
          {PRODUCT_NAME}
        </h1>
        {openProjectName !== null && (
          <p className="m-0 truncate font-mono text-sm opacity-60">
            {openProjectName}
          </p>
        )}
      </header>

      <div className="grid min-h-0 grid-cols-1 lg:grid-cols-[20rem_1fr]">
        <RunList
          runs={runs}
          refusal={runsRefusal}
          openRunId={runId}
          onOpen={openRun}
        />

        <div className="grid min-h-0 min-w-0 grid-rows-[auto_1fr] bg-card">
          <SectionTabs
            sections={sections}
            openSection={openSection}
            onOpenSection={setOpenSection}
            disabled={run === null}
          />

          <main className="pane min-w-0 px-6 pt-8 pb-24 sm:px-10">
            {answerRefusal !== null && <Refusal text={answerRefusal} />}
            {readRefusal !== null && <Refusal text={readRefusal} />}

            {run === null ? (
              <p className="max-w-prose text-ink-soft">
                Nothing is shown until the application answers for a run. Choose
                one from the list beside this.
              </p>
            ) : (
              <div className="max-w-5xl">
                {sections.map(
                  (section) =>
                    section.id === openSection && (
                      <Section
                        key={section.id}
                        number={section.number}
                        name={section.name}
                        headingId={`${section.id}-heading`}
                        count={section.count}
                      >
                        {section.body}
                      </Section>
                    ),
                )}
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

// Tabs, not buttons: choosing which part of a run to read is navigation, and
// the only things on this screen that act on a run are Approve, Reject and
// Finish review.
function SectionTabs({ sections, openSection, onOpenSection, disabled }) {
  if (disabled) {
    return <div className="h-12 border-b border-line-strong" />;
  }
  return (
    <div
      role="tablist"
      aria-label="Sections of this run"
      className="flex flex-wrap items-stretch border-b border-line-strong"
    >
      {sections.map((section) => {
        const open = section.id === openSection;
        return (
          <button
            key={section.id}
            role="tab"
            type="button"
            aria-selected={open}
            aria-controls={`${section.id}-heading`}
            onClick={() => onOpenSection(section.id)}
            className={`-mb-px flex items-center gap-2 border-r border-line px-5 py-3 font-mono text-xs font-semibold tracking-wide whitespace-nowrap ${
              open
                ? "border-b-2 border-b-ink bg-signal"
                : "text-ink-soft hover:bg-signal/15 hover:text-ink"
            }`}
          >
            {section.tab}
            {section.tabCount !== null && section.tabCount !== undefined && (
              <span
                className={`px-1.5 py-0.5 text-[11px] ${
                  section.tabWaiting
                    ? "border border-signal-edge bg-signal text-ink"
                    : "bg-line text-ink"
                }`}
              >
                {section.tabCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function Refusal({ text }) {
  return (
    <p
      className="mb-8 border-2 border-danger bg-card px-5 py-4"
      role="alert"
    >
      <span className="eyebrow mb-1 block text-danger">the server refused</span>
      {text}
    </p>
  );
}

function Skipped({ skipped }) {
  if (skipped.length === 0) {
    return <p className="m-0 text-ink-soft">This run skipped nothing.</p>;
  }
  return (
    <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2">
      {skipped.map((entry, place) => (
        <li key={place} className="border border-line bg-card px-4 py-3">
          <dl className="m-0 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
            {/* A skip states its own fields — a file with its reason, or a
                dropped quote with the words that were not found. Rendering the
                keys the server sent shows both without inventing a shape for
                either. */}
            {Object.entries(entry).map(([name, value]) => (
              <div key={name} className="contents">
                <dt className="eyebrow">{name}</dt>
                <dd className="m-0 text-sm">{value}</dd>
              </div>
            ))}
          </dl>
        </li>
      ))}
    </ul>
  );
}

function Decisions({
  decisions,
  examine,
  reviewing,
  answering,
  waiting,
  onAnswer,
  onFinish,
}) {
  return (
    <>
      {decisions.length === 0 ? (
        <p className="m-0 text-ink-soft">This run has raised no decision.</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {decisions.map((decision) => (
            <Question
              key={decision.decision_id}
              decision={decision}
              reviewing={reviewing}
              answering={answering}
              onAnswer={onAnswer}
            />
          ))}
        </ul>
      )}
      {examine !== null && (
        <div className="mt-8 border-t border-line pt-5">
          <Examine examine={examine} />
        </div>
      )}
      <FinishReview
        reviewing={reviewing}
        unanswered={waiting}
        answering={answering}
        onFinish={onFinish}
      />
    </>
  );
}

// Both rules belong to the server: it refuses a run that is not at review, and
// it refuses a review with an unanswered decision. The button is offered only
// where the run the server just described allows it.
function FinishReview({ reviewing, unanswered, answering, onFinish }) {
  if (!reviewing) {
    return (
      <p className="mt-8 text-sm text-ink-soft">
        This run is not at review, so nothing can be answered on it now.
      </p>
    );
  }
  if (unanswered > 0) {
    return (
      <p className="mt-8 text-sm text-ink-soft">
        {unanswered} decision(s) are unanswered, so the server will refuse to
        finish this review.
      </p>
    );
  }
  return (
    <button
      type="button"
      disabled={answering}
      onClick={onFinish}
      className="edge-shadow mt-8 border-2 border-signal-edge bg-signal px-6 py-3 font-mono text-sm font-semibold disabled:opacity-40"
    >
      Finish review
    </button>
  );
}

function RegisterSection({ exported }) {
  if (exported === null) {
    return (
      <p className="m-0 max-w-prose text-sm text-ink-soft">
        This run has not exported a register, so there is nothing here to show.
        The register is exported once the export decision is approved and the run
        commits.
      </p>
    );
  }
  return <Register exported={exported} />;
}

// Every figure here is the server's: the durations it recorded, the tokens the
// model reported to it, and the estimate it made from them. Where it has none,
// the word is "unknown" — never a zero, which would read as a measurement.
function CostAndTiming({ reported }) {
  const unknownCost = reported.estimated_cost_usd === null;
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-3">
        <Figure
          label="Total time"
          value={
            reported.stages.length === 0 ? "nothing finished yet" : `${reported.total_seconds}s`
          }
        />
        <Figure
          label="Tokens reported"
          value={
            reported.tokens.prompt === null
              ? "unknown"
              : `${reported.tokens.prompt} + ${reported.tokens.completion}`
          }
          note={`${reported.tokens.calls_reporting_usage} of ${
            reported.tokens.calls_reporting_usage + reported.tokens.calls_without_usage
          } calls reported what they spent`}
        />
        <Figure
          label="Estimated cost, USD"
          value={unknownCost ? "unknown" : reported.estimated_cost_usd}
          note={unknownCost ? reported.cost_unknown_reason : "estimated"}
        />
      </div>

      {reported.stages.length === 0 ? (
        <p className="mt-5 text-sm text-ink-soft">
          No stage of this run has finished, so no duration is recorded yet.
        </p>
      ) : (
        <dl className="mt-8 grid grid-cols-[max-content_1fr] gap-x-8 gap-y-1.5 font-mono text-sm">
          {reported.stages.map((stage) => (
            <div key={stage.stage} className="contents">
              <dt className="text-ink-soft">{stage.stage}</dt>
              <dd className="m-0">{stage.seconds} seconds</dd>
            </div>
          ))}
          <div className="contents">
            <dt className="text-ink-soft">Every stage together</dt>
            <dd className="m-0">{reported.total_seconds} seconds</dd>
          </div>
        </dl>
      )}

      <p className="mt-5 max-w-prose text-sm text-ink-soft">{reported.estimate_note}</p>
    </>
  );
}

function Figure({ label, value, note }) {
  return (
    <div className="border border-line bg-card px-4 py-3">
      <p className="eyebrow m-0">{label}</p>
      <p className="m-0 mt-2 font-mono text-2xl">{value}</p>
      {note !== undefined && (
        <p className="m-0 mt-1.5 text-sm text-ink-soft">{note}</p>
      )}
    </div>
  );
}
