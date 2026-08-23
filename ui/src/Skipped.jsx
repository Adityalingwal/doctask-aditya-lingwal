// The label each kind of skipped entry wears, and the only source of one. A
// kind this map does not hold renders with no label at all: a wrong label is
// worse than none, and the server may learn a kind before this screen does.
const SKIPPED_LABELS = {
  "read before": "Read before",
  "not read": "Not read",
  "not attached": "Not attached to any row",
};

const KIND_ORDER = ["read before", "not read", "not attached"];

/**
 * What a run did not use, in three groups by kind. Every sentence here is the
 * server's: the file name, the reason, the observation's own summary and the
 * line naming where it was found. This file groups and aligns them and writes
 * no word of its own (S21).
 */
export default function Skipped({ entries }) {
  if (entries.length === 0) {
    return <p className="m-0 text-ink-soft">Nothing in this run was skipped.</p>;
  }
  const unknownKinds = entries
    .map((entry) => entry.kind)
    .filter((kind) => !Object.hasOwn(SKIPPED_LABELS, kind));
  return (
    <div className="flex flex-col gap-7">
      {[...KIND_ORDER, ...new Set(unknownKinds)].map((kind) => (
        <Group
          key={kind}
          label={Object.hasOwn(SKIPPED_LABELS, kind) ? SKIPPED_LABELS[kind] : null}
          entries={entries.filter((entry) => entry.kind === kind)}
        />
      ))}
    </div>
  );
}

function Group({ label, entries }) {
  if (entries.length === 0) {
    return null;
  }
  return (
    <section>
      {label !== null && <h3 className="eyebrow m-0 mb-3">{label}</h3>}
      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {entries.map((entry, place) => (
          <li key={place} className="border-l-2 border-line pl-4 text-[15px]">
            {entry.summary === undefined ? (
              <FileLine entry={entry} />
            ) : (
              <ObservationLines entry={entry} />
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

// A whole file the run did not read: its name, then the reason, in one column
// so a long reason wraps under itself rather than under the file name.
function FileLine({ entry }) {
  if (entry.file === undefined) {
    return <p className="m-0">{entry.reason}</p>;
  }
  return (
    <p className="skipped-line m-0">
      <span className="font-mono font-semibold">{entry.file}</span>
      <span aria-hidden="true">—</span>
      <span>{entry.reason}</span>
    </p>
  );
}

// Something a document said that reached no row is titled by what it says,
// never by the file (item 38). Its place is named only when the server found
// one: a quote the file never held has nowhere to point at, and the reason
// names the file instead (S12).
function ObservationLines({ entry }) {
  return (
    <>
      <p className="m-0">&ldquo;{entry.summary}&rdquo;</p>
      {entry.source_line !== undefined && entry.source_line !== null && (
        <p className="m-0 mt-1 pl-4 font-mono text-xs text-ink-soft">
          {entry.source_line}
        </p>
      )}
      <p className="m-0 mt-1 pl-4 text-sm text-ink-soft">{entry.reason}</p>
    </>
  );
}
