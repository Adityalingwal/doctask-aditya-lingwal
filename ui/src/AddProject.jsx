import { useState } from "react";

import Refusal from "./Refusal.jsx";
import { createProject, startRun } from "./run_requests.js";

const NO_FOLDER_CHECK = "Choose the folder to watch.";
const NO_FOLDER_LEFT = "No folder left to add.";

// An empty folder makes a project and starts no run, refused identically
// through the endpoint, the MCP tool and the watcher (locked change (a)). The
// button says which of the two is about to happen, so nobody presses "start"
// and is then told there was nothing to start.
const CREATE_ONLY = "Create project";
const CREATE_AND_RUN = "Create and start run";

// The box L8's button opens: folder, and nothing else — there is no name
// field, because a project's name is derived from its folder, in core, never
// supplied here (D-family for folder-is-a-project). It checks only that a
// folder is chosen (L9) — every other rule, including whether the folder
// actually exists, stays the server's, and is shown exactly as it answered,
// under "Could not create this project" rather than "the server refused"
// (screen 2). What it tells its parent is one thing — the run the server
// started, or the project it created with no run — and the parent decides
// what happens next (L5).
export default function AddProject({
  projectsRoot,
  availableFolders,
  hasFilesByFolder,
  projects,
  onStarted,
  onCreated,
  onClose,
  onUnreachable,
}) {
  const [sourceFolderPath, setSourceFolderPath] = useState("");
  const [ownCheck, setOwnCheck] = useState(null);
  // Held so a retry after a failed `POST /runs` skips `POST /projects` (L4).
  // Set only once `POST /projects` has actually succeeded, and never cleared
  // by a run-start failure — only a fresh box carries a fresh attempt.
  const [projectId, setProjectId] = useState(null);
  const [refusal, setRefusal] = useState(null);
  const [starting, setStarting] = useState(false);

  // The dropdown lists only folders that do not already carry a project
  // (section 1.5): the difference between every folder the projects root
  // holds and every project's own `source_folder_path`.
  const takenFolders = new Set(projects.map((project) => project.source_folder_path));
  const openFolders = availableFolders.filter((folder) => !takenFolders.has(folder));
  // Only a folder the server has actually reported as empty switches the
  // button: before one is chosen, and for a folder the answer says nothing
  // about, the ordinary ending is the one offered.
  const chosenFolderIsEmpty =
    sourceFolderPath !== ""
    && (hasFilesByFolder ?? {})[sourceFolderPath] === false;

  const start = async (submitted) => {
    submitted.preventDefault();
    if (sourceFolderPath === "") {
      setOwnCheck(NO_FOLDER_CHECK);
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
      const created = await createProject(sourceFolderPath);
      if (!created.ok) {
        stopOn(created);
        return;
      }
      usableProjectId = created.body.project_id;
      setProjectId(usableProjectId);
    }

    // The server would refuse a run on an empty folder, so this asks for no
    // run at all: the folder is watched from now on, and the first file put
    // there starts the first run by itself.
    if (chosenFolderIsEmpty) {
      await onCreated(usableProjectId);
      return;
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
            className="cursor-pointer font-mono text-sm text-ink-soft hover:text-ink active:translate-y-px"
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
            {/* The browser's own dropdown paints a rounded, shaded control
                that belongs to no other part of this screen. `appearance-none`
                takes that away and leaves the same square border, mono type
                and focus edge every other field here wears (item 1). */}
            <select
              value={sourceFolderPath}
              onChange={(changed) => setSourceFolderPath(changed.target.value)}
              disabled={openFolders.length === 0}
              className="w-full cursor-pointer appearance-none border border-line-strong bg-card bg-[right_0.75rem_center] bg-no-repeat px-3 py-2 pr-9 font-mono text-sm select-caret hover:border-signal-edge focus:border-signal-edge focus:outline-2 focus:outline-offset-2 focus:outline-signal-edge disabled:cursor-not-allowed disabled:bg-paper disabled:text-ink-soft"
            >
              {openFolders.length === 0 ? (
                <option value="">{NO_FOLDER_LEFT}</option>
              ) : (
                <>
                  <option value="">Choose a folder</option>
                  {openFolders.map((folder) => (
                    <option key={folder} value={folder}>
                      {folder}
                    </option>
                  ))}
                </>
              )}
            </select>
            <span className="mt-1 block text-xs text-ink-soft">
              {projectsRoot === null
                ? "The folders shown here come from the application."
                : `New folders go inside ${projectsRoot}/ — a person puts one there; this screen never creates one by itself.`}
            </span>
          </label>

          <button
            type="submit"
            disabled={starting}
            className="edge-shadow mt-6 w-full cursor-pointer border-2 border-signal-edge bg-signal px-6 py-3 font-mono text-sm font-semibold hover:bg-signal/70 active:translate-x-0.5 active:translate-y-0.5 active:shadow-none disabled:cursor-not-allowed disabled:opacity-40"
          >
            {chosenFolderIsEmpty ? CREATE_ONLY : CREATE_AND_RUN}
          </button>
        </form>
      </div>
    </div>
  );
}
