import { useState } from "react";

import Refusal from "./Refusal.jsx";
import { createProject, startRun } from "./run_requests.js";

const EMPTY_NAME_CHECK = "Give this project a name.";
const NO_FOLDER_CHECK = "Choose the folder to watch.";

// The box L8's button opens: folder first, then name (screen 2), and nothing
// else. It checks only that both are non-empty (L9) — every other rule,
// including whether the folder actually exists, stays the server's, and is
// shown exactly as it answered, under "Could not create this project" rather
// than "the server refused" (screen 2). What it tells its parent is one
// thing, the id of the run the server started; the parent decides what
// happens next (L5), the same as the start-a-run form it replaces.
export default function AddProject({
  projectsRoot,
  availableFolders,
  onStarted,
  onClose,
  onUnreachable,
}) {
  const [sourceFolderPath, setSourceFolderPath] = useState("");
  const [name, setName] = useState("");
  const [nameEditedByUser, setNameEditedByUser] = useState(false);
  const [ownCheck, setOwnCheck] = useState(null);
  // Held so a retry after a failed `POST /runs` skips `POST /projects` (L4)
  // — `projects.name` carries no unique constraint, so creating a second
  // project over the same folder would leave the watcher polling it twice.
  // Set only once `POST /projects` has actually succeeded, and never cleared
  // by a run-start failure — only a fresh box carries a fresh attempt.
  const [projectId, setProjectId] = useState(null);
  const [refusal, setRefusal] = useState(null);
  const [starting, setStarting] = useState(false);

  const chooseFolder = (chosen) => {
    setSourceFolderPath(chosen);
    if (!nameEditedByUser) {
      setName(nameDerivedFromFolder(chosen));
    }
  };

  const start = async (submitted) => {
    submitted.preventDefault();
    if (sourceFolderPath === "") {
      setOwnCheck(NO_FOLDER_CHECK);
      return;
    }
    if (name.trim() === "") {
      setOwnCheck(EMPTY_NAME_CHECK);
      return;
    }
    setOwnCheck(null);
    setRefusal(null);
    setStarting(true);

    // Screen 11: a request that never reached the application is not a
    // refusal. The strip under the header says so once, and this box says
    // nothing rather than blaming a server that never answered.
    const stopOn = (acted) => {
      if (acted.unreachable) {
        setRefusal(null);
        onUnreachable();
      } else {
        setRefusal(acted.refusal);
      }
      setStarting(false);
    };

    let usableProjectId = projectId;
    if (usableProjectId === null) {
      const created = await createProject(name, sourceFolderPath);
      if (!created.ok) {
        stopOn(created);
        return;
      }
      usableProjectId = created.body.project_id;
      setProjectId(usableProjectId);
    }

    const started = await startRun(usableProjectId);
    if (!started.ok) {
      stopOn(started);
      return;
    }
    // `starting` is deliberately left set. The parent's re-read is a round
    // trip, and this box stays mounted through it; a live button there takes
    // a second click and starts another run, which the server does not
    // refuse — it queues one behind the first.
    await onStarted(started.body.run_id);
  };

  return (
    <div
      className="fixed inset-0 z-10 flex items-center justify-center bg-ink/40 px-4"
      onClick={(clicked) => {
        if (clicked.target === clicked.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="edge-shadow w-full max-w-sm border-2 border-line-strong bg-card p-6">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="m-0 font-mono text-sm font-semibold tracking-tight">
            Add project
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="font-mono text-sm text-ink-soft hover:text-ink"
          >
            ×
          </button>
        </div>

        {ownCheck !== null && (
          <p className="mb-5 border-2 border-danger bg-card px-4 py-3 text-sm" role="alert">
            {ownCheck}
          </p>
        )}
        {refusal !== null && (
          <Refusal text={refusal} heading="Could not create this project" />
        )}

        <form onSubmit={start}>
          <label className="block">
            <span className="eyebrow mb-1 block">Folder</span>
            <select
              value={sourceFolderPath}
              onChange={(changed) => chooseFolder(changed.target.value)}
              className="w-full border border-line-strong bg-card px-3 py-2 font-mono text-sm"
            >
              <option value="">Choose a folder</option>
              {availableFolders.map((folder) => (
                <option key={folder} value={folder}>
                  {folder}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-xs text-ink-soft">
              {projectsRoot === null
                ? "The folders shown here come from the application."
                : `New folders go inside ${projectsRoot}/ — a person puts one there; this screen never creates one by itself.`}
            </span>
          </label>

          <label className="mt-5 block">
            <span className="eyebrow mb-1 block">Project name</span>
            <input
              type="text"
              value={name}
              onChange={(changed) => {
                setNameEditedByUser(true);
                setName(changed.target.value);
              }}
              placeholder="Northside Dental"
              className="w-full border border-line-strong bg-card px-3 py-2 text-[15px]"
            />
          </label>

          <button
            type="submit"
            disabled={starting}
            className="edge-shadow mt-6 w-full border-2 border-signal-edge bg-signal px-6 py-3 font-mono text-sm font-semibold disabled:opacity-40"
          >
            Create and start run
          </button>
        </form>
      </div>
    </div>
  );
}

function nameDerivedFromFolder(folderPath) {
  const segment = folderPath.split("/").pop() ?? "";
  return segment
    .split(/[-_]+/)
    .filter((word) => word !== "")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}
