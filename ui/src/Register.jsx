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

export default function Register({ exported }) {
  return (
    <>
      <p>
        Exported at {exported.exported_at} from run {exported.run_id}, project{" "}
        {exported.project.name}.
      </p>
      <table>
        <thead>
          <tr>
            <th scope="col">#</th>
            {exported.columns.map((column) => (
              <th key={column} scope="col">
                {CELL_HEADINGS[column] ?? column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {exported.rows.map((row) => (
            <tr key={row.row_number}>
              <th scope="row">{row.row_number}</th>
              {exported.columns.map((column) => (
                <td key={column}>{row.cells[column]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Evidence</h3>
      {exported.rows.map((row) => (
        <div key={row.row_number} className="row-evidence">
          <h4>Row {row.row_number}</h4>
          <ul>
            {row.citations.map((citation, place) => (
              <li key={place}>{citationLine(citation)}</li>
            ))}
          </ul>
          {row.findings.length > 0 && (
            <ul>
              {row.findings.map((finding) => (
                <li key={finding.rule_id}>{findingLine(finding)}</li>
              ))}
            </ul>
          )}
        </div>
      ))}

      <h3>Rules and findings</h3>
      <Examine examine={exported.examine} />
    </>
  );
}

export function Examine({ examine }) {
  return (
    <>
      <p>Rules run against {examine.rows_examined} register row(s):</p>
      <ul>
        {examine.rules.map((rule) => (
          <li key={rule.id}>
            {rule.id} — {rule.text}
            {rule.params === undefined ? "" : ` (${settingsOf(rule.params)})`}
          </li>
        ))}
      </ul>
      {examine.findings.length === 0 ? (
        <p>No findings — no register row broke one of those rules.</p>
      ) : (
        <ul>
          {examine.findings.map((finding, place) => (
            <li key={place}>{findingLine(finding)}</li>
          ))}
        </ul>
      )}
    </>
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
