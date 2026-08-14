import { useCallback, useEffect, useState } from "react";

import Question from "./Question.jsx";
import Register, { Examine } from "./Register.jsx";
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

  return (
    <main>
      <h1>Requirements-to-Delivery Register — run review</h1>
      <OpenRun runId={runId} onOpen={setRunId} />
      {answerRefusal !== null && (
        <p className="refusal" role="alert">
          {answerRefusal}
        </p>
      )}
      {readRefusal !== null && (
        <p className="refusal" role="alert">
          {readRefusal}
        </p>
      )}
      {run === null ? (
        <p>Nothing is shown until the application answers for a run id.</p>
      ) : (
        <>
          <Stages run={run} />
          <Skipped skipped={run.skipped} />
          <Decisions
            decisions={run.decisions}
            examine={run.examine}
            reviewing={run.status === WAITING_FOR_REVIEW}
            answering={answering}
            onAnswer={answer}
            onFinish={finish}
          />
          <RegisterSection exported={exported} />
          <CostAndTiming reported={run.cost_and_timing} />
        </>
      )}
    </main>
  );
}

function OpenRun({ runId, onOpen }) {
  const [typed, setTyped] = useState(runId);
  return (
    <form
      className="open-run"
      onSubmit={(submitted) => {
        submitted.preventDefault();
        onOpen(typed.trim());
      }}
    >
      <label htmlFor="run-id">Run id</label>
      <input
        id="run-id"
        name="run-id"
        value={typed}
        onChange={(typing) => setTyped(typing.target.value)}
      />
      <button type="submit">Show run</button>
    </form>
  );
}

function Stages({ run }) {
  return (
    <section aria-labelledby="stages-heading">
      <h2 id="stages-heading">Stages</h2>
      <dl>
        <dt>Run</dt>
        <dd>{run.run_id}</dd>
        <dt>Project</dt>
        <dd>{run.project_id}</dd>
        <dt>Status</dt>
        <dd>{run.status}</dd>
        <dt>Stage</dt>
        <dd>{run.stage === null ? "no stage recorded yet" : run.stage}</dd>
      </dl>
      {run.ended_early_reason !== null && (
        <p>Ended early: {run.ended_early_reason}</p>
      )}
      {run.failure_reason !== null && <p>Failure: {run.failure_reason}</p>}
    </section>
  );
}

function Skipped({ skipped }) {
  return (
    <section aria-labelledby="skipped-heading">
      <h2 id="skipped-heading">Skipped</h2>
      {skipped.length === 0 ? (
        <p>This run skipped nothing.</p>
      ) : (
        <ul>
          {skipped.map((entry, place) => (
            <li key={place}>
              <dl>
                {/* A skip states its own fields — a file with its reason, or a
                    dropped quote with the words that were not found. Rendering
                    the keys the server sent shows both without inventing a
                    shape for either. */}
                {Object.entries(entry).map(([name, value]) => (
                  <div key={name}>
                    <dt>{name}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Decisions({
  decisions,
  examine,
  reviewing,
  answering,
  onAnswer,
  onFinish,
}) {
  const unanswered = decisions.filter((decision) => decision.outcome === null);
  return (
    <section aria-labelledby="decisions-heading">
      <h2 id="decisions-heading">Needs your decision</h2>
      {decisions.length === 0 ? (
        <p>This run has raised no decision.</p>
      ) : (
        <ul className="questions">
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
      {examine !== null && <Examine examine={examine} />}
      <FinishReview
        reviewing={reviewing}
        unanswered={unanswered.length}
        answering={answering}
        onFinish={onFinish}
      />
    </section>
  );
}

// Both rules belong to the server: it refuses a run that is not at review, and
// it refuses a review with an unanswered decision. The button is offered only
// where the run the server just described allows it.
function FinishReview({ reviewing, unanswered, answering, onFinish }) {
  if (!reviewing) {
    return <p>This run is not at review, so nothing can be answered on it now.</p>;
  }
  if (unanswered > 0) {
    return (
      <p>
        {unanswered} decision(s) are unanswered, so the server will refuse to
        finish this review.
      </p>
    );
  }
  return (
    <button type="button" disabled={answering} onClick={onFinish}>
      Finish review
    </button>
  );
}

function RegisterSection({ exported }) {
  return (
    <section aria-labelledby="register-heading">
      <h2 id="register-heading">Register</h2>
      {exported === null ? (
        <p>
          This run has not exported a register, so there is nothing here to
          show. The register is exported once the export decision is approved
          and the run commits.
        </p>
      ) : (
        <Register exported={exported} />
      )}
    </section>
  );
}

// Every figure here is the server's: the durations it recorded, the tokens the
// model reported to it, and the estimate it made from them. Where it has none,
// the word is "unknown" — never a zero, which would read as a measurement.
function CostAndTiming({ reported }) {
  const unknownCost = reported.estimated_cost_usd === null;
  return (
    <section aria-labelledby="cost-heading">
      <h2 id="cost-heading">Cost and timing</h2>
      {reported.stages.length === 0 ? (
        <p>No stage of this run has finished, so no duration is recorded yet.</p>
      ) : (
        <dl>
          {reported.stages.map((stage) => (
            <div key={stage.stage}>
              <dt>{stage.stage}</dt>
              <dd>{stage.seconds} seconds</dd>
            </div>
          ))}
          <div>
            <dt>Every stage together</dt>
            <dd>{reported.total_seconds} seconds</dd>
          </div>
        </dl>
      )}
      <dl>
        <div>
          <dt>Prompt tokens the model reported</dt>
          <dd>{reported.tokens.prompt === null ? "unknown" : reported.tokens.prompt}</dd>
        </div>
        <div>
          <dt>Completion tokens the model reported</dt>
          <dd>
            {reported.tokens.completion === null
              ? "unknown"
              : reported.tokens.completion}
          </dd>
        </div>
        <div>
          <dt>Calls that reported what they spent</dt>
          <dd>
            {reported.tokens.calls_reporting_usage} of{" "}
            {reported.tokens.calls_reporting_usage +
              reported.tokens.calls_without_usage}
          </dd>
        </div>
        <div>
          <dt>Estimated cost, USD</dt>
          <dd>
            {unknownCost
              ? `unknown — ${reported.cost_unknown_reason}`
              : `${reported.estimated_cost_usd} (estimated)`}
          </dd>
        </div>
      </dl>
      <p>{reported.estimate_note}</p>
    </section>
  );
}
