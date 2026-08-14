import { useState } from "react";

import Refusal from "./Refusal.jsx";
import { createProject, startRun } from "./run_requests.js";

// The screen's one way in for a first-time user: two fields and a button,
// nothing else (L2). It validates nothing — an empty name, a blank folder, a
// folder that does not exist are all sent to the server exactly as typed, and
// whatever sentence the server refuses with is shown unchanged (L3). What it
// tells its parent is one thing, the id of the run the server started; the
// parent decides what happens next (L5).
export default function StartRun({ onStarted }) {
  const [name, setName] = useState("");
  const [sourceFolderPath, setSourceFolderPath] = useState("");
  // Held so a retry after a failed `POST /runs` skips `POST /projects`
  // (L4) — `projects.name` carries no unique constraint, so creating a
  // second project over the same folder would leave the watcher polling it
  // twice. This is set only once `POST /projects` has actually succeeded, and
  // is never cleared by a run-start failure — only a fresh page carries a
  // fresh attempt.
  const [projectId, setProjectId] = useState(null);
  const [refusal, setRefusal] = useState(null);
  const [starting, setStarting] = useState(false);

  const start = async (submitted) => {
    submitted.preventDefault();
    setStarting(true);
    setRefusal(null);

    let usableProjectId = projectId;
    if (usableProjectId === null) {
      const created = await createProject(name, sourceFolderPath);
      if (!created.ok) {
        setRefusal(created.refusal);
        setStarting(false);
        return;
      }
      usableProjectId = created.body.project_id;
      setProjectId(usableProjectId);
    }

    const started = await startRun(usableProjectId);
    if (!started.ok) {
      setRefusal(started.refusal);
      setStarting(false);
      return;
    }
    // `starting` is deliberately left set. The parent's re-read is a round
    // trip, and this form stays mounted through it; a live button there takes
    // a second click and starts another run, which the server does not refuse
    // — it queues one behind the first.
    await onStarted(started.body.run_id);
  };

  return (
    <div className="max-w-sm">
      {refusal !== null && <Refusal text={refusal} />}
      <form onSubmit={start}>
        <label className="block">
          <span className="eyebrow mb-1 block">Project name</span>
          <input
            type="text"
            value={name}
            onChange={(changed) => setName(changed.target.value)}
            placeholder="Northside Dental"
            className="w-full border border-line-strong bg-card px-3 py-2 text-[15px]"
          />
        </label>

        <label className="mt-5 block">
          <span className="eyebrow mb-1 block">
            Folder its documents arrive in
          </span>
          <input
            type="text"
            value={sourceFolderPath}
            onChange={(changed) => setSourceFolderPath(changed.target.value)}
            placeholder="sample-projects/northside-dental"
            className="w-full border border-line-strong bg-card px-3 py-2 font-mono text-sm"
          />
          {/* L6: the application only ever reads inside its own container, so
              a folder outside the repository is refused, correctly, by the
              server this sends to. */}
          <span className="mt-1 block text-xs text-ink-soft">
            Read inside the repository — for example
            {" "}
            <code className="font-mono">sample-projects/northside-dental</code>.
          </span>
        </label>

        <button
          type="submit"
          disabled={starting}
          className="edge-shadow mt-6 border-2 border-signal-edge bg-signal px-6 py-3 font-mono text-sm font-semibold disabled:opacity-40"
        >
          Start run
        </button>
      </form>
    </div>
  );
}
