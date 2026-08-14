// One component for every gate. The kind, the question and the answer are all
// read off the decision the server froze, so a possible match, a conflict, a
// withdrawal, a rule finding and the export gate render through this same code
// with no branch on which of them it is.
export default function Question({ decision, reviewing, onAnswer, answering }) {
  return (
    <li className="question">
      <p className="question-kind">{decision.kind}</p>
      <p className="question-text">{decision.question}</p>
      <p className="question-answer">
        Answer: {decision.outcome === null ? "unanswered" : decision.outcome}
      </p>
      {reviewing && (
        // An answer may change until finish-review (D02), so a decision the
        // server already recorded keeps both buttons while the run is at
        // review; the screen never closes a window the server leaves open.
        <p className="question-actions">
          <button
            type="button"
            disabled={answering}
            onClick={() => onAnswer(decision.decision_id, "approved")}
          >
            Approve
          </button>
          <button
            type="button"
            disabled={answering}
            onClick={() => onAnswer(decision.decision_id, "rejected")}
          >
            Reject
          </button>
        </p>
      )}
    </li>
  );
}
