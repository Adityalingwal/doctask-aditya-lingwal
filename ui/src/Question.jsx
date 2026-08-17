const FINDING_KIND = "finding";
const POSSIBLE_MATCH_KIND = "possible match";
const OBSERVATION_MATCH_KIND = "observation match";

// One component for every gate. The kind and the answer are read off the
// decision the server froze, so a possible match, a conflict, a rule finding
// and the export gate render through this same code with no branch on which
// of them it is — except a finding's own body (screen 4), which the flat
// `question` sentence cannot carry without a rule code in it.
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
      <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-line px-5 py-3">
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

      {decision.kind === FINDING_KIND ? (
        <FindingBody decision={decision} />
      ) : (
        <StoredQuestion question={decision.question} />
      )}

      <WhatTheAnswersDo decision={decision} />

      {reviewing && (
        // An answer may change until finish-review (D02), so a decision the
        // server already recorded keeps both buttons while the run is at
        // review; the screen never closes a window the server leaves open.
        <p className="m-0 flex gap-3 border-t border-line px-5 py-4">
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

// One decision can cover several observations, and each of them carries its
// own sentence. They are stacked as they were written, so each becomes its own
// paragraph here — nothing joins them into a sentence nobody wrote.
function StoredQuestion({ question }) {
  return (
    <div className="px-5 py-5">
      {question.split("\n\n").map((paragraph, place) => (
        <p
          key={place}
          className={`m-0 max-w-prose text-[17px] leading-relaxed ${
            place === 0 ? "" : "mt-4"
          }`}
        >
          {paragraph}
        </p>
      ))}
    </div>
  );
}

// What Approve and Reject will do is a fact the server knows, so it is fixed
// text beside values the server computed — never part of the stored question,
// which is frozen the moment it is raised and must not describe the buttons.
function WhatTheAnswersDo({ decision }) {
  const answers = whatEachAnswerDoes(decision);
  if (answers === null) {
    return null;
  }
  return (
    <dl className="m-0 grid grid-cols-[max-content_1fr] gap-x-5 gap-y-3 border-t border-line px-5 py-4 text-[15px]">
      <dt className="eyebrow whitespace-nowrap">Approve</dt>
      <dd className="m-0 max-w-prose">{answers.approve}</dd>
      <dt className="eyebrow whitespace-nowrap">Reject</dt>
      <dd className="m-0 max-w-prose">{answers.reject}</dd>
    </dl>
  );
}

// A possible match shows only the shape, because the new `Written down?` is
// worked out inside Commit and not when the question is raised. An observation
// match shows the values, because they were computed and stored before the
// question was raised and that same stored move is what Commit applies.
function whatEachAnswerDoes(decision) {
  if (decision.kind === POSSIBLE_MATCH_KIND) {
    return { approve: "one row", reject: "a separate row" };
  }
  if (decision.kind === OBSERVATION_MATCH_KIND) {
    return {
      approve: (
        <>
          row #{decision.row_number} records:
          <ul className="m-0 mt-2 list-none p-0">
            {decision.moved_cells.map((moved) => (
              <li key={moved.cell}>{`${moved.cell}: ${moved.value}`}</li>
            ))}
          </ul>
        </>
      ),
      reject: "nothing changes on the register",
    };
  }
  if (decision.kind === FINDING_KIND) {
    return {
      approve: `the finding is attached to row #${decision.row_number} and appears in the register`,
      reject:
        "the finding stays in this run's record and never reaches the register",
    };
  }
  return null;
}

// A finding in three labelled parts, and never a rule code: the rule's own
// words, the row and what it did to break the rule, and the evidence — no
// R1, no D1, anywhere on this screen (screen 4).
function FindingBody({ decision }) {
  return (
    <dl className="m-0 grid grid-cols-[max-content_1fr] gap-x-5 gap-y-4 px-5 py-5">
      <dt className="eyebrow whitespace-nowrap">Rule</dt>
      <dd className="m-0 max-w-prose text-[15px] leading-relaxed">
        {decision.rule_text}
      </dd>
      <dt className="eyebrow whitespace-nowrap">Row {decision.row_number} breaks it</dt>
      <dd className="m-0 max-w-prose text-[15px] leading-relaxed">{decision.issue}</dd>
      <dt className="eyebrow whitespace-nowrap">Evidence</dt>
      <dd className="m-0 max-w-prose text-[15px] leading-relaxed">{decision.evidence}</dd>
    </dl>
  );
}

function AnswerButton({ label, answering, onClick }) {
  return (
    <button
      type="button"
      disabled={answering}
      onClick={onClick}
      className="edge-shadow-sm border border-line-strong bg-card px-5 py-2 font-mono text-sm font-semibold hover:bg-paper disabled:opacity-40"
    >
      {label}
    </button>
  );
}
