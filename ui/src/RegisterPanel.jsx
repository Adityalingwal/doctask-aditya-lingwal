import Register from "./Register.jsx";

/**
 * The project's own panel (section 2.3): the register, read live from its
 * committed rows, and the panel a row opens beside it. The whole project's
 * history is no longer a section here — a row's own history is read inside
 * that row's panel, where the reader is already looking, and the full trail
 * stays readable over `GET /projects/{id}/history` and the `get_history`
 * tool (item 6a, 2026-08-25).
 *
 * The empty state covers a new project, a first run still working, and a run
 * whose changes were discarded — every case in which no run has committed
 * rows, which the server answers as a register holding none — with one line,
 * never an empty table.
 */
export default function RegisterPanel({ exported, read, history }) {
  const empty = exported === null || exported.rows.length === 0;
  const entries = history === null ? [] : history.entries;
  return (
    <section aria-labelledby="register-panel-heading">
      <h2
        id="register-panel-heading"
        className="m-0 mb-7 flex items-center gap-2 border-b border-line pb-5"
      >
        <span className="section-name">Register</span>
        {read && !empty && (
          <span className="bg-line px-1.5 py-0.5 font-mono text-[11px] text-ink">
            {exported.rows.length}
          </span>
        )}
      </h2>

      {!read ? (
        // Until the read answers this screen knows nothing about this
        // register, and saying it is empty would be a claim the server has
        // not made.
        <p className="m-0 max-w-prose text-sm text-ink-soft">
          Reading this register…
        </p>
      ) : empty ? (
        <p className="m-0 max-w-prose text-sm text-ink-soft">
          Nothing has been added to this register yet.
        </p>
      ) : (
        <Register exported={exported} history={entries} />
      )}
    </section>
  );
}
