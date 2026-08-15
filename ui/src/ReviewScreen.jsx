import { useCallback, useEffect, useState } from "react";

import { useScrollbarWhileScrolling } from "./scrollbar_while_scrolling.js";

import Question from "./Question.jsx";
import Refusal from "./Refusal.jsx";
import Register, { Examine } from "./Register.jsx";
import RunList from "./RunList.jsx";
import Section, { WaitingCount } from "./Section.jsx";
import Stages from "./Stages.jsx";
import StartRun from "./StartRun.jsx";
import screenConfig from "../config/screen.json";
import {
  answerDecision,
  finishReview,
  readExport,
  readRun,
  readRuns,
} from "./run_requests.js";

// The one status in which the server accepts an answer or a finished review.
const WAITING_FOR_REVIEW = "needs review";

// The screen's own name. The register it shows keeps the name the decisions and
// the exports give it; this is only what the person looking at it calls the
// thing, and it lives in one place so it can be changed in one place.
const PRODUCT_NAME = "Register";

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
  // Before the first read comes back, "the application answered with no runs"
  // and "the application has not been asked yet" hold the same two values — an
  // empty list and no refusal. Only this tells them apart, and without it the
  // start form is offered over an application that has said nothing.
  const [runsAnswered, setRunsAnswered] = useState(false);
  const [openSection, setOpenSection] = useState("stages");
  const readingPane = useScrollbarWhileScrolling();

  const readListFromServer = useCallback(async () => {
    const answered = await readRuns();
    setRuns(answered.ok ? answered.body.runs : []);
    setRunsRefusal(answered.ok ? null : answered.refusal);
    setRunsAnswered(true);
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

  // L5: nothing the person typed into the start form reaches the screen. The
  // list is re-read and the run the server actually created is what gets
  // opened — never the id or the fields that were submitted.
  const startedRun = useCallback(
    async (startedRunId) => {
      await readListFromServer();
      openRun(startedRunId);
    },
    [readListFromServer, openRun],
  );

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
      </header>

      <div className="grid min-h-0 grid-cols-1 lg:grid-cols-[20rem_1fr]">
        <RunList
          runs={runs}
          refusal={runsRefusal}
          openRunId={runId}
          onOpen={openRun}
        />

        <div className="grid min-h-0 min-w-0 grid-rows-[auto_1fr] bg-card">
          <div className="border-b border-line px-6 pt-7 pb-5 sm:px-10">
            <p className="eyebrow m-0">project</p>
            <p className="m-0 mt-1 text-2xl leading-tight font-semibold">
              {openProjectName ?? "This run"}
            </p>
            <SectionTabs
              sections={sections}
              openSection={openSection}
              onOpenSection={setOpenSection}
              disabled={run === null}
            />
          </div>

          <main ref={readingPane} className="pane min-w-0 px-6 pt-8 pb-24 sm:px-10">
            {answerRefusal !== null && <Refusal text={answerRefusal} />}
            {readRefusal !== null && <Refusal text={readRefusal} />}

            {run === null ? (
              // L1: the form stands in for this paragraph only once the list
              // read has actually answered and come back with zero runs — a
              // refusal (runsRefusal !== null) keeps the paragraph, because a
              // form here would say "start one" over an application that could
              // not be reached, and so does a read that has not answered yet.
              runsAnswered && runs.length === 0 && runsRefusal === null ? (
                <StartRun onStarted={startedRun} />
              ) : (
                <p className="max-w-prose text-ink-soft">
                  Nothing is shown until the application answers for a run.
                  Choose one from the list beside this.
                </p>
              )
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
    return null;
  }
  return (
    <div
      role="tablist"
      aria-label="Sections of this run"
      className="mt-6 flex flex-wrap items-stretch gap-3"
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
            className={`flex items-center gap-2 border px-4 py-2 font-mono text-xs font-semibold tracking-wide whitespace-nowrap ${
              open
                ? "edge-shadow-sm border-signal-edge bg-signal text-ink"
                : "border-line text-ink-soft hover:border-line-strong hover:text-ink"
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

