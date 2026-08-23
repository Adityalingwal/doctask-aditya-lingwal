import { useState } from "react";

import History, { runsInHistory } from "./History.jsx";
import Register from "./Register.jsx";

const REGISTER_TAB = "register";
const HISTORY_TAB = "history";

/**
 * The project's own panel (section 2.3): the register read live from its
 * committed rows, and beside it the history of how it came to say what it
 * says. The empty state covers a new project, a first run still working, and
 * a run whose changes were discarded — every case in which no run has
 * committed rows, which the server answers as a register holding none — with
 * one line, never an empty table.
 */
export default function RegisterPanel({ exported, read, history }) {
  const [openTab, setOpenTab] = useState(REGISTER_TAB);
  const empty = exported === null || exported.rows.length === 0;
  const entries = history === null ? [] : history.entries;
  return (
    <section aria-labelledby="register-panel-heading">
      <h2 id="register-panel-heading" className="m-0">
        <span className="section-name">Register</span>
      </h2>

      <div
        role="tablist"
        aria-label="The project's register"
        className="mt-5 mb-7 flex flex-wrap items-stretch gap-3 border-b border-line pb-5"
      >
        <PanelTab
          id={REGISTER_TAB}
          label="Register"
          count={read && !empty ? String(exported.rows.length) : null}
          openTab={openTab}
          onOpen={setOpenTab}
        />
        <PanelTab
          id={HISTORY_TAB}
          label="History"
          count={
            history === null ? null : `${runsInHistory(entries)} runs`
          }
          openTab={openTab}
          onOpen={setOpenTab}
        />
      </div>

      {openTab === REGISTER_TAB ? (
        <div id={`${REGISTER_TAB}-panel`} role="tabpanel" aria-label="Register">
          {!read ? (
            // Until the read answers this screen knows nothing about this
            // register, and saying it is empty would be a claim the server
            // has not made.
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
        </div>
      ) : (
        // Only once the server has answered — an empty list is this register
        // having no history, which is not the same claim as not having been
        // asked yet.
        <div id={`${HISTORY_TAB}-panel`} role="tabpanel" aria-label="History">
          {history === null ? (
            <p className="m-0 max-w-prose text-sm text-ink-soft">
              Reading this history…
            </p>
          ) : (
            <History entries={entries} />
          )}
        </div>
      )}
    </section>
  );
}

function PanelTab({ id, label, count, openTab, onOpen }) {
  const open = id === openTab;
  return (
    <button
      role="tab"
      type="button"
      aria-selected={open}
      aria-controls={`${id}-panel`}
      onClick={() => onOpen(id)}
      className={`flex cursor-pointer items-center gap-2 border px-4 py-2 font-mono text-xs font-semibold tracking-wide whitespace-nowrap active:translate-y-px ${
        open
          ? "edge-shadow-sm border-signal-edge bg-signal text-ink hover:bg-signal/80"
          : "border-line text-ink-soft hover:border-line-strong hover:bg-paper hover:text-ink active:bg-signal/25"
      }`}
    >
      {label}
      {count !== null && (
        <span className="bg-line px-1.5 py-0.5 text-[11px] text-ink">{count}</span>
      )}
    </button>
  );
}
