import Question from "./Question.jsx";
import Stages from "./Stages.jsx";
import { Examine } from "./Register.jsx";

const WAITING_FOR_REVIEW = "needs review";

const WAITING_LINE = "This run is waiting for you.";
const ADD_LABEL = "Add this run's changes to the register";
const DISCARD_LABEL = "Discard this run's changes";

/**
 * One run, top to bottom: what each stage did, why it stopped early, what it
 * is waiting for, the decisions it raised, and the rules it judged against.
 */
export default function RunTab({
  run,
  decisions,
  waiting,
  answering,
  onAnswer,
  onFinish,
}) {
  const reviewing = run.status === WAITING_FOR_REVIEW;
  return (
    <div className="flex flex-col gap-8">
      <Stages run={run} />

      {reviewing && (
        <WaitingForYou
          waiting={waiting}
          answering={answering}
          onFinish={onFinish}
        />
      )}

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

      {run.examine !== null && (
        <section aria-labelledby="rules-and-findings-heading">
          <h3 id="rules-and-findings-heading" className="eyebrow m-0 mb-3">
            Rules and findings
          </h3>
          <Examine examine={run.examine} />
        </section>
      )}
    </div>
  );
}

// Both endings belong to the server: it refuses a review with an unanswered
// decision, so the adding button is disabled rather than hidden — a person
// must be able to see what finishing looks like before they have finished.
// Neither ending is louder than the other: a screen that makes one look like
// the expected answer is answering for the person.
function WaitingForYou({ waiting, answering, onFinish }) {
  return (
    <div>
      <p className="m-0 text-[17px]">
        {WAITING_LINE}
        {waiting > 0 && (
          <span className="text-ink-soft">
            {" "}
            — {waiting} decision{waiting === 1 ? "" : "s"} to answer
          </span>
        )}
      </p>
      <p className="m-0 mt-4 flex flex-wrap gap-3">
        <EndReviewButton
          label={ADD_LABEL}
          disabled={answering || waiting > 0}
          onClick={() => onFinish(true)}
        />
        <EndReviewButton
          label={DISCARD_LABEL}
          disabled={answering}
          onClick={() => onFinish(false)}
        />
      </p>
    </div>
  );
}

function EndReviewButton({ label, disabled, onClick }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="edge-shadow cursor-pointer border-2 border-signal-edge bg-signal px-6 py-3 font-mono text-sm font-semibold hover:bg-signal/70 active:translate-x-0.5 active:translate-y-0.5 active:shadow-none disabled:cursor-not-allowed disabled:opacity-40"
    >
      {label}
    </button>
  );
}
