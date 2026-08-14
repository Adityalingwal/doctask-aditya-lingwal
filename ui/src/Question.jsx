// One component for every gate. The kind, the question and the answer are all
// read off the decision the server froze, so a possible match, a conflict, a
// withdrawal, a rule finding and the export gate render through this same code
// with no branch on which of them it is.
//
// The accent is on the left edge of a decision nobody has answered yet, and it
// is the only accent in the card: Approve and Reject look identical, because a
// screen that makes one answer louder is answering for the person.
export default function Question({ decision, reviewing, onAnswer, answering }) {
  const unanswered = decision.outcome === null;
  return (
    <li
      className={`border border-line bg-card ${
        unanswered ? "border-l-4 border-l-signal-edge" : ""
      }`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-line px-4 py-2">
        <p className="eyebrow m-0">{decision.kind}</p>
        <p className="m-0 font-mono text-[11px]">
          {unanswered ? (
            <span className="border border-signal-edge bg-signal px-2 py-0.5 font-semibold">
              unanswered
            </span>
          ) : (
            <span className="text-ink-soft">{decision.outcome}</span>
          )}
        </p>
      </div>

      <p className="m-0 max-w-prose px-4 py-4 text-[15px] leading-relaxed">
        {decision.question}
      </p>

      {reviewing && (
        // An answer may change until finish-review (D02), so a decision the
        // server already recorded keeps both buttons while the run is at
        // review; the screen never closes a window the server leaves open.
        <p className="m-0 flex gap-3 border-t border-line px-4 py-3">
          <AnswerButton
            label="Approve"
            answering={answering}
            onClick={() => onAnswer(decision.decision_id, "approved")}
          />
          <AnswerButton
            label="Reject"
            answering={answering}
            onClick={() => onAnswer(decision.decision_id, "rejected")}
          />
        </p>
      )}
    </li>
  );
}

function AnswerButton({ label, answering, onClick }) {
  return (
    <button
      type="button"
      disabled={answering}
      onClick={onClick}
      className="edge-shadow-sm border border-line-strong bg-card px-4 py-1.5 font-mono text-xs font-semibold hover:bg-paper disabled:opacity-40"
    >
      {label}
    </button>
  );
}
