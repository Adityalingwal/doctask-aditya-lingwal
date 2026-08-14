import screenConfig from "../config/screen.json";

// D05 fixes the seven cell names; the export sends the column keys, not the
// words a person reads. An unknown key is shown as the server sent it rather
// than turned into a heading nobody chose.
const CELL_HEADINGS = {
  what_was_asked: "What was asked",
  in_writing: "In writing?",
  what_testing_found: "What testing found",
  status: "Status",
  blocked_on: "Blocked on",
  first_seen: "First seen",
  last_moved: "Last moved",
};

const STATUS_CELL = "status";

export default function Register({ exported }) {
  return (
    <>
      <p className="eyebrow m-0 mb-4">
        {exported.project.name} · exported {exported.exported_at} · run{" "}
        {exported.run_id}
      </p>

      <div className="overflow-x-auto border border-line bg-card">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-line-strong">
              <th scope="col" className="eyebrow px-3 py-2 text-left">
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
                  className="px-3 py-3 text-left align-top font-mono text-xs font-normal text-ink-soft"
                >
                  {row.row_number}
                </th>
                {exported.columns.map((column) => (
                  <td key={column} className="px-3 py-3 align-top">
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
          <div key={row.row_number} className="border border-line bg-card px-4 py-3">
            <h4 className="eyebrow m-0 mb-2">Row {row.row_number}</h4>
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {row.citations.map((citation, place) => (
                <li key={place} className="text-sm">
                  {citationLine(citation)}
                </li>
              ))}
            </ul>
            {row.findings.length > 0 && (
              <ul className="m-0 mt-3 flex list-none flex-col gap-2 border-t border-line p-0 pt-3">
                {row.findings.map((finding) => (
                  <li key={finding.rule_id} className="text-sm">
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
        rules run against {examine.rows_examined} register row(s)
      </p>
      <ul className="m-0 flex list-none flex-col gap-1 p-0 font-mono text-xs">
        {examine.rules.map((rule) => (
          <li key={rule.id}>
            <span className="mr-2 font-semibold">{rule.id}</span>
            {rule.text}
            {rule.params === undefined ? "" : ` (${settingsOf(rule.params)})`}
          </li>
        ))}
      </ul>
      {examine.findings.length === 0 ? (
        <p className="mt-3 text-sm text-ink-soft">
          No findings — no register row broke one of those rules.
        </p>
      ) : (
        <ul className="m-0 mt-3 flex list-none flex-col gap-2 p-0">
          {examine.findings.map((finding, place) => (
            <li
              key={place}
              className="border-l-4 border-caution bg-card py-2 pl-3 text-sm"
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
      className={`inline-block border px-2 py-0.5 font-mono text-[11px] whitespace-nowrap ${
        needsAttention ? "border-caution text-caution" : "border-line text-ink"
      }`}
    >
      {status}
    </span>
  );
}

// A citation is never shown without the file it came from: a quote carries the
// place the reader derived, and an absence carries the statement instead.
function citationLine(citation) {
  if (citation.source_words === null) {
    return `${citation.cell} — ${citation.source_file}: ${citation.absence_statement}`;
  }
  return (
    `${citation.cell} — ${citation.source_file}, ${citation.place}: `
    + `"${citation.source_words}"`
  );
}

function findingLine(finding) {
  return (
    `Row ${finding.row_number} ${finding.rule_id} — ${finding.issue} `
    + `(${finding.evidence})`
  );
}

function settingsOf(params) {
  return Object.entries(params)
    .map(([name, value]) => `${name}: ${value}`)
    .join(", ");
}
