import { useEffect, useRef, useState } from "react";

import Refusal from "./Refusal.jsx";
import { createProject, startRun } from "./run_requests.js";

const NO_FOLDER_CHECK = "Choose the folder to watch.";
const NO_FOLDER_LEFT = "No folder left to add.";
const NOTHING_CHOSEN_YET = "Choose a folder";
const FOLDER_LABEL = "Folder";

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
          <div className="block">
            <span id="folder-field-label" className="eyebrow mb-1 block">
              {FOLDER_LABEL}
            </span>
            <FolderDropdown
              folders={openFolders}
              chosen={sourceFolderPath}
              onChoose={setSourceFolderPath}
            />
            <span className="mt-1 block text-xs text-ink-soft">
              {projectsRoot === null
                ? "The folders shown here come from the application."
                : `New folders go inside ${projectsRoot}/ — a person puts one there; this screen never creates one by itself.`}
            </span>
          </div>

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

// The browser's own open menu is a rounded panel in the operating system's
// style that CSS cannot reach, and it was the one thing on this screen drawn
// by somebody else. Button and listbox instead, so the open list wears the
// same square border, hard shadow and mono type as every other control
// (item 1). The closed control keeps exactly the look it already had.
function FolderDropdown({ folders, chosen, onChoose }) {
  const [open, setOpen] = useState(false);
  const [keyboardRow, setKeyboardRow] = useState(0);
  const dropdown = useRef(null);
  const control = useRef(null);
  const empty = folders.length === 0;

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const closeOnOutsideClick = (clicked) => {
      if (!dropdown.current?.contains(clicked.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("click", closeOnOutsideClick);
    return () => document.removeEventListener("click", closeOnOutsideClick);
  }, [open]);

  const close = () => {
    setOpen(false);
    control.current?.focus();
  };

  const pick = (folder) => {
    onChoose(folder);
    close();
  };

  const move = (by) => {
    setKeyboardRow((row) => {
      const next = row + by;
      if (next < 0) {
        return folders.length - 1;
      }
      return next >= folders.length ? 0 : next;
    });
  };

  const readKey = (pressed) => {
    if (pressed.key === "Escape" && open) {
      pressed.preventDefault();
      close();
      return;
    }
    if (pressed.key === "ArrowDown" || pressed.key === "ArrowUp") {
      pressed.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      move(pressed.key === "ArrowDown" ? 1 : -1);
      return;
    }
    if (pressed.key === "Enter" && open) {
      pressed.preventDefault();
      pick(folders[keyboardRow]);
    }
  };

  return (
    <div ref={dropdown} className="relative" onKeyDown={readKey}>
      <button
        ref={control}
        type="button"
        aria-labelledby="folder-field-label"
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={empty}
        onClick={() => {
          setKeyboardRow(Math.max(folders.indexOf(chosen), 0));
          setOpen((was) => !was);
        }}
        className={`folder-caret w-full cursor-pointer border border-line-strong bg-card px-3 py-2 pr-9 text-left font-mono text-sm hover:border-signal-edge focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal-edge disabled:cursor-not-allowed disabled:bg-paper disabled:text-ink-soft ${
          open ? "folder-caret-up border-signal-edge" : ""
        }`}
      >
        {empty ? NO_FOLDER_LEFT : chosen || NOTHING_CHOSEN_YET}
      </button>

      {open && (
        <ul
          role="listbox"
          aria-labelledby="folder-field-label"
          className="edge-shadow absolute top-full right-0 left-0 z-10 mt-1 max-h-56 overflow-y-auto border border-line-strong bg-card font-mono text-sm"
        >
          {folders.map((folder, row) => (
            <li
              key={folder}
              role="option"
              aria-selected={folder === chosen}
              onClick={() => pick(folder)}
              onMouseEnter={() => setKeyboardRow(row)}
              className={`flex cursor-pointer items-center justify-between border-b border-line px-3 py-2 last:border-b-0 ${
                row === keyboardRow ? "bg-signal" : ""
              }`}
            >
              {folder}
              {folder === chosen && (
                <span aria-hidden="true" className="font-semibold text-signal-edge">
                  ✓
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
