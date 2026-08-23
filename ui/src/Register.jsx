import screenConfig from "../config/screen.json";
import { dayMonthTime } from "./format_date.js";

// D05 fixes the four cell names; the export sends the column keys, not the
// words a person reads. An unknown key is shown as the server sent it rather
// than turned into a heading nobody chose. The stored column is still
// `in_writing`; only the heading asks the question in a reader's words.
// Exported because the history section names the same cells, and two copies of
// this map are two places for a heading to be renamed in only one of them.
export const CELL_HEADINGS = {
  what_was_asked: "What was asked",
  in_writing: "Written down",
  what_testing_found: "What testing found",
  status: "Status",
};

const STATUS_CELL = "status";

export default function Register({ exported }) {
  return (
    <>
      <p className="eyebrow m-0 mb-4">
        {exported.project.name} · last updated {dayMonthTime(exported.exported_at)}
      </p>

      <div className="overflow-x-auto border border-line bg-card">
        <table className="w-full border-collapse text-[15px]">
          <thead>
            <tr className="border-b border-line-strong">
              <th scope="col" className="eyebrow px-4 py-3 text-left">
                #
              </th>
              {exported.columns.map((column) => (
                <th key={column} scope="col" className="eyebrow px-3 py-2 text-left">
                  {CELL_HEADINGS[column] ?? column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {exported.rows.map((row) => (
              <tr key={row.row_number} className="border-b border-line last:border-b-0">
                <th
                  scope="row"
                  className="px-4 py-3.5 text-left align-top font-mono text-sm font-normal text-ink-soft"
                >
                  {row.row_number}
                </th>
                {exported.columns.map((column) => (
                  <td key={column} className="px-4 py-3.5 align-top">
                    {column === STATUS_CELL ? (
                      <StatusChip status={row.cells[column]} />
                    ) : (
                      row.cells[column]
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="eyebrow mt-8 mb-3">Evidence</h3>
      <div className="grid gap-3">
        {exported.rows.map((row) => (
          <div key={row.row_number} className="border border-line bg-card px-5 py-4">
            <h4 className="eyebrow m-0 mb-2">Row {row.row_number}</h4>
            <ul className="m-0 flex list-none flex-col gap-3 p-0">
              {row.citations.map((citation, place) => (
                <li key={place}>
                  <Citation citation={citation} />
                </li>
              ))}
            </ul>
            {(row.findings ?? []).length > 0 && (
              <ul className="m-0 mt-3 flex list-none flex-col gap-2 border-t border-line p-0 pt-3">
                {(row.findings ?? []).map((finding) => (
                  <li
                    key={finding.rule_id}
                    className="border-l-4 border-caution py-1 pl-4"
                  >
                    {findingLine(finding)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>

      <h3 className="eyebrow mt-8 mb-3">Rules and findings</h3>
      <Examine examine={exported.examine} />
    </>
  );
}

export function Examine({ examine }) {
  return (
    <>
      <p className="eyebrow m-0 mb-3">
        {plural(examine.rules.length, "rule")} ran against{" "}
        {plural(examine.rows_examined, "row")}
      </p>
      <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
        {examine.rules.map((rule) => (
          <li key={rule.id} className="flex gap-2">
            <span aria-hidden="true">·</span>
            <span>{foldedRuleText(rule)}</span>
          </li>
        ))}
      </ul>
      {examine.findings.length === 0 ? (
        <p className="mt-4 text-ink-soft">
          No findings — no row broke any of these rules.
        </p>
      ) : (
        <ul className="m-0 mt-3 flex list-none flex-col gap-2 p-0">
          {examine.findings.map((finding, place) => (
            <li
              key={place}
              className="border-l-4 border-caution bg-card py-2 pl-4"
            >
              {findingLine(finding)}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

// A status the configuration calls out is marked; every other status is shown
// plainly. The words themselves are the register's, never rewritten here.
function StatusChip({ status }) {
  const needsAttention = screenConfig.attention_statuses.includes(status);
  return (
    <span
      className={`inline-block border px-2.5 py-1 font-mono text-xs whitespace-nowrap ${
        needsAttention ? "border-caution text-caution" : "border-line text-ink"
      }`}
    >
      {status}
    </span>
  );
}

// A citation is never shown without the file it came from: a quote carries the
// place the reader derived, and an absence carries the statement instead. The
// two are drawn differently because they are different claims — one says a
// document said this, the other says a document stopped saying it.
function Citation({ citation }) {
  const quoted = citation.source_words !== null;
  const cellHeading = CELL_HEADINGS[citation.cell] ?? citation.cell;
  return (
    <>
      <p className="eyebrow m-0">
        {cellHeading} · {citation.source_file}
        {quoted && citation.place !== null ? ` · ${citation.place}` : ""}
      </p>
      {quoted ? (
        <p className="m-0 mt-1.5 border-l-2 border-line-strong pl-4">
          &ldquo;{citation.source_words}&rdquo;
        </p>
      ) : (
        <p className="m-0 mt-1.5 border-l-2 border-line pl-4 text-ink-soft italic">
          {citation.absence_statement}
        </p>
      )}
    </>
  );
}

function findingLine(finding) {
  return `Row ${finding.row_number} — ${finding.issue} (${finding.evidence})`;
}

// A rule's own parameters, folded into its sentence: a rule whose text names
// a setting is shown with the value the run judged against in that word's
// place, never printed after the sentence as "(max_days: 14)".
function foldedRuleText(rule) {
  const params = rule.params ?? {};
  return Object.entries(params).reduce(
    (text, [name, value]) => text.replaceAll(name, String(value)),
    rule.text,
  );
}

function plural(count, noun) {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}
