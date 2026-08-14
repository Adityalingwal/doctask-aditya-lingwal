import { useCallback, useEffect, useState } from "react";

import Question from "./Question.jsx";
import Register, { Examine } from "./Register.jsx";
import Section, { WaitingCount } from "./Section.jsx";
import Stages from "./Stages.jsx";
import screenConfig from "../config/screen.json";
import {
  answerDecision,
  finishReview,
  readExport,
  readRun,
} from "./run_requests.js";

// The one status in which the server accepts an answer or a finished review.
const WAITING_FOR_REVIEW = "waiting for review";

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
    const polling = setInterval(readFromServer, screenConfig.poll_interval_ms);
    return () => clearInterval(polling);
  }, [readFromServer]);

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

  return (
    <div className="min-h-screen">
      <header className="border-b border-line-strong bg-card">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <h1 className="m-0 font-mono text-base font-semibold tracking-tight">
            Requirements-to-Delivery Register
            <span className="ml-3 font-normal text-ink-soft">run review</span>
          </h1>
          <OpenRun runId={runId} onOpen={setRunId} />
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 pb-24">
        {answerRefusal !== null && <Refusal text={answerRefusal} />}
        {readRefusal !== null && <Refusal text={readRefusal} />}

        {run === null ? (
          <p className="mt-10 text-sm text-ink-soft">
            Nothing is shown until the application answers for a run id.
          </p>
        ) : (
          <div className="mt-10 flex flex-col gap-10">
            <Section number="01" name="Stages" headingId="stages-heading">
              <Stages run={run} />
            </Section>

            <Section
              number="02"
              name="Skipped"
              headingId="skipped-heading"
              count={`${run.skipped.length} skipped`}
            >
              <Skipped skipped={run.skipped} />
            </Section>

            <Section
              number="03"
              name="Needs your decision"
              headingId="decisions-heading"
              count={<WaitingCount waiting={waiting} />}
            >
              <Decisions
                decisions={run.decisions}
                examine={run.examine}
                reviewing={run.status === WAITING_FOR_REVIEW}
                answering={answering}
                waiting={waiting}
                onAnswer={answer}
                onFinish={finish}
              />
            </Section>

            <Section
              number="04"
              name="Register"
              headingId="register-heading"
              count={exported === null ? "not exported" : `${exported.rows.length} rows`}
            >
              <RegisterSection exported={exported} />
            </Section>

            <Section
              number="05"
              name="Cost and timing"
              headingId="cost-heading"
              count="estimate, not a bill"
            >
              <CostAndTiming reported={run.cost_and_timing} />
            </Section>
          </div>
        )}
      </main>
    </div>
  );
}

function Refusal({ text }) {
  return (
    <p
      className="mt-6 border border-danger bg-card px-4 py-3 text-sm"
      role="alert"
    >
      <span className="eyebrow block text-danger">the server refused</span>
      {text}
    </p>
  );
}

function OpenRun({ runId, onOpen }) {
  const [typed, setTyped] = useState(runId);
  return (
    <form
      className="flex flex-wrap items-center gap-2"
      onSubmit={(submitted) => {
        submitted.preventDefault();
        onOpen(typed.trim());
      }}
    >
      <label htmlFor="run-id" className="eyebrow">
        Run id
      </label>
      <input
        id="run-id"
        name="run-id"
        value={typed}
        onChange={(typing) => setTyped(typing.target.value)}
        className="w-64 border border-line-strong bg-paper px-2 py-1 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-signal-edge"
      />
      <button
        type="submit"
        className="edge-shadow-sm border border-line-strong bg-card px-3 py-1 font-mono text-xs font-semibold hover:bg-paper"
      >
        Show run
      </button>
    </form>
  );
}

function Skipped({ skipped }) {
  if (skipped.length === 0) {
    return <p className="m-0 text-sm text-ink-soft">This run skipped nothing.</p>;
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
        <p className="m-0 text-sm text-ink-soft">This run has raised no decision.</p>
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
        <dl className="mt-6 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 font-mono text-xs">
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
      <p className="m-0 mt-1 font-mono text-lg">{value}</p>
      {note !== undefined && (
        <p className="m-0 mt-1 text-xs text-ink-soft">{note}</p>
      )}
    </div>
  );
}
