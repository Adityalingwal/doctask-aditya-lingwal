const APPROVED = "approved";
const REJECTED = "rejected";

// The two markers `app/review/decision_text.py` writes in front of each
// consequence sentence. The sentence after the marker is the server's; this
// screen puts it in the column beside the button rather than repeating the
// word the button already says.
const APPROVE_MARKER = "Approve → ";
const REJECT_MARKER = "Reject → ";

const BLOCKS_SEPARATED_BY = "\n\n";
const LINES_SEPARATED_BY = "\n";

/**
 * One decision card. Every sentence on it was written by the backend and is
 * carried in `question`, blocks separated by a blank line; the parts beside it
 * say what each block is, so this file can lay them out without reading a
 * single one (S21). The only joining it does is the row block's cell values,
 * which are data rather than wording.
 */
export default function Question({ decision, reviewing, onAnswer, answering }) {
  const unanswered = decision.outcome === null;
  const blocks = decisionBlocks(decision);
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

      <div className="px-5 py-5">
        {decision.row !== null && <RowBlock row={decision.row} />}

        {blocks.rule !== null && (
          <p className="m-0 mt-5 max-w-prose text-[15px] leading-relaxed">
            {blocks.rule}
          </p>
        )}
        {blocks.issue !== null && (
          <p className="m-0 mt-3 max-w-prose text-[15px] leading-relaxed">
            {blocks.issue}
          </p>
        )}

        {blocks.quotes.map((quote, place) => (
          <div key={place} className="mt-5">
            <p className="eyebrow m-0">{quote.sourceLine}</p>
            <p className="m-0 mt-1.5 max-w-prose border-l-2 border-line-strong pl-4 text-[15px]">
              {quote.words}
            </p>
          </div>
        ))}

        <p className="m-0 mt-6 max-w-prose text-[17px] leading-relaxed">
          {blocks.question}
        </p>
      </div>

      {/* One grid for both answers, so each label and the sentence beside it
          start on the same line however long either of them runs. */}
      <dl className="decision-lines m-0 items-baseline gap-y-3 border-t border-line px-5 py-4 text-[15px]">
        <dt className="m-0">
          {reviewing ? (
            <AnswerButton
              label="Approve"
              chosen={decision.outcome === APPROVED}
              answering={answering}
              onClick={() => onAnswer(decision.decision_id, APPROVED)}
            />
          ) : (
            <span className="eyebrow">Approve</span>
          )}
        </dt>
        <dd className="m-0 max-w-prose">{blocks.approve}</dd>
        <dt className="m-0">
          {reviewing ? (
            <AnswerButton
              label="Reject"
              chosen={decision.outcome === REJECTED}
              answering={answering}
              onClick={() => onAnswer(decision.decision_id, REJECTED)}
            />
          ) : (
            <span className="eyebrow">Reject</span>
          )}
        </dt>
        <dd className="m-0 max-w-prose">{blocks.reject}</dd>
      </dl>
    </li>
  );
}

/**
 * The stored text, cut back into the blocks it was built from.
 *
 * Which block is which is read off the parts — a rule line exists exactly when
 * `rule_text` does, an issue line exactly when `issue` does, and there are as
 * many quote blocks as `quotes` — never by looking at what a block says. No
 * sentence is parsed, matched or rebuilt: each is handed on whole.
 */
function decisionBlocks(decision) {
  const blocks = decision.question.split(BLOCKS_SEPARATED_BY);
  let next = 1;
  const rule = decision.rule_text === null ? null : blocks[next++];
  const issue = decision.issue === null ? null : blocks[next++];
  const quotes = blocks
    .slice(next, next + decision.quotes.length)
    .map(quoteBlock);
  const [approve, reject] = blocks[blocks.length - 1].split(LINES_SEPARATED_BY);
  return {
    rule,
    issue,
    quotes,
    question: blocks[next + decision.quotes.length],
    approve: withoutMarker(approve, APPROVE_MARKER),
    reject: withoutMarker(reject, REJECT_MARKER),
  };
}

// A quote block is the line naming where the words are, then the words. Split
// so the two can be set apart from each other; neither is changed.
function quoteBlock(block) {
  const lines = block.split(LINES_SEPARATED_BY);
  return { sourceLine: lines[0], words: lines.slice(1).join(LINES_SEPARATED_BY) };
}

function withoutMarker(line, marker) {
  return line.startsWith(marker) ? line.slice(marker.length) : line;
}

// The row the decision is about, as the register's own table shows it: the
// label the backend chose — a committed row and one this same run proposed do
// not read the same (S24) — above its four cells under their full column
// names.
function RowBlock({ row }) {
  return (
    <div className="border border-line bg-paper px-4 py-3">
      <p className="eyebrow m-0 mb-2">{row.label}</p>
      <dl className="decision-lines m-0 gap-y-1 text-[15px]">
        {Object.entries(row.cells).map(([heading, value]) => (
          <div key={heading} className="contents">
            <dt className="text-ink-soft">{heading}</dt>
            <dd className="m-0">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

// The answer the server has recorded is the one wearing the accent, and it
// keeps wearing it while the run is at review — an answer may be changed
// until the review is finished (D02), so the other button stays live rather
// than going quiet the moment one is pressed.
function AnswerButton({ label, chosen, answering, onClick }) {
  return (
    <button
      type="button"
      disabled={answering}
      aria-pressed={chosen}
      onClick={onClick}
      className={`edge-shadow-sm w-full cursor-pointer border px-5 py-2 font-mono text-sm font-semibold active:translate-x-px active:translate-y-px disabled:cursor-not-allowed disabled:opacity-40 ${
        chosen
          ? "border-signal-edge bg-signal text-ink hover:bg-signal/70"
          : "border-line-strong bg-card hover:bg-paper"
      }`}
    >
      {label}
    </button>
  );
}
