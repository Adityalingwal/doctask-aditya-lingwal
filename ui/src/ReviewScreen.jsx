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
  const [refusal, setRefusal] = useState(null);
  const [answering, setAnswering] = useState(false);

  const readFromServer = useCallback(async () => {
    if (runId === "") {
      return;
    }
    const answered = await readRun(runId);
    if (!answered.ok) {
      setRun(null);
      setExported(null);
      setRefusal(answered.refusal);
      return;
    }
    setRun(answered.body);
    if (!answered.body.exported) {
      setExported(null);
      return;
    }
    const register = await readExport(runId);
    setExported(register.ok ? register.body : null);
    if (!register.ok) {
      setRefusal(register.refusal);
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
      setRefusal(answered.ok ? null : answered.refusal);
      await readFromServer();
      setAnswering(false);
    },
    [runId, readFromServer],
  );

  const finish = useCallback(async () => {
    setAnswering(true);
    const finished = await finishReview(runId);
    setRefusal(finished.ok ? null : finished.refusal);
    await readFromServer();
    setAnswering(false);
  }, [runId, readFromServer]);

  return (
    <main>
      <h1>Requirements-to-Delivery Register — run review</h1>
      <OpenRun runId={runId} onOpen={setRunId} />
      {refusal !== null && (
        <p className="refusal" role="alert">
          {refusal}
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
          <CostAndTiming />
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

function CostAndTiming() {
  return (
    <section aria-labelledby="cost-heading">
      <h2 id="cost-heading">Cost and timing</h2>
      <p>
        The API reports no cost or timing for a run yet, so nothing is shown
        here rather than a number nobody measured. The operations slice adds
        stage durations and the token roll-up.
      </p>
    </section>
  );
}
