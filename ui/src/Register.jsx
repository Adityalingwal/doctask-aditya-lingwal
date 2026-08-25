import { useState } from "react";

import RowDrawer from "./RowDrawer.jsx";
import screenConfig from "../config/screen.json";
import { dayMonthTime } from "./format_date.js";

// D05 fixes the four cell names; the export sends the column keys, not the
// words a person reads. An unknown key is shown as the server sent it rather
// than turned into a heading nobody chose. The stored column is still
// `in_writing`; only the heading asks the question in a reader's words.
// Exported because the history section and the row panel name the same cells,
// and two copies of this map are two places for a heading to be renamed in
// only one of them.
export const CELL_HEADINGS = {
  what_was_asked: "What was asked",
  in_writing: "Written down",
  what_testing_found: "What testing found",
  status: "Status",
};

const STATUS_CELL = "status";

/**
 * The register as a table, and one row at a time in the panel it opens. The
 * rules a run judged against are not here: they belong to the run that ran
 * them, and the Run tab keeps them (item 15).
 */
export default function Register({ exported, history }) {
  const [openRowNumber, setOpenRowNumber] = useState(null);
  const openRow =
    exported.rows.find((row) => row.row_number === openRowNumber) ?? null;
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
                Row
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
              <tr
                key={row.row_number}
                onClick={() => setOpenRowNumber(row.row_number)}
                className="cursor-pointer border-b border-line last:border-b-0 hover:bg-signal/15 active:bg-signal/30"
              >
                <th
                  scope="row"
                  className="px-4 py-3.5 text-left align-top font-mono text-sm font-normal text-ink-soft"
                >
                  {row.row_number}
                </th>
                {exported.columns.map((column) => (
                  <td key={column} className="px-4 py-3.5 align-top">
                    {column === STATUS_CELL ? (
                      <>
                        <StatusChip status={row.cells[column]} />
                        <FindingMark findings={row.findings} />
                      </>
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

      {openRow !== null && (
        <RowDrawer
          row={openRow}
          columns={exported.columns}
          history={history}
          onClose={() => setOpenRowNumber(null)}
        />
      )}
    </>
  );
}

// Item 43: the mark exists only where findings do. A clean row carries no
// `findings` key at all, so nothing is counted and nothing is drawn — never
// "0 findings". What each finding says lives in the panel, not in the cell.
function FindingMark({ findings }) {
  const raised = (findings ?? []).length;
  if (raised === 0) {
    return null;
  }
  return (
    <span className="mt-1.5 block font-mono text-xs text-caution">
      {raised} finding{raised === 1 ? "" : "s"}
    </span>
  );
}

// Said when a run judged nothing at all, and said alone: a run whose rules
// every one named a kind of document this project has not read yet found no
// finding because it looked for none, and "no findings" there would report a
// clean register nobody examined (item 8).
const NO_RULE_RAN = "No rule ran.";
const NO_FINDINGS = "No findings.";

export function Examine({ examine }) {
  if (examine.rules.length === 0) {
    return <p className="m-0 text-ink-soft">{NO_RULE_RAN}</p>;
  }
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
        <p className="mt-4 text-ink-soft">{NO_FINDINGS}</p>
      ) : (
        <ul className="m-0 mt-3 flex list-none flex-col gap-2 p-0">
          {examine.findings.map((finding) => (
            <li
              key={finding.finding_id}
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

// The issue sentence is the backend's; the row prefix is the same data join
// history lines use. The evidence is not repeated here — the decision card
// already shows it in full.
function findingLine(finding) {
  return `Row ${finding.row_number} · ${finding.issue}`;
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
