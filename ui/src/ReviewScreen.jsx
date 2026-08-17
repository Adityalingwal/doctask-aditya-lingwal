import { useCallback, useEffect, useRef, useState } from "react";

import { useScrollbarWhileScrolling } from "./scrollbar_while_scrolling.js";

import AddProject from "./AddProject.jsx";
import ProjectList from "./ProjectList.jsx";
import Question from "./Question.jsx";
import Refusal from "./Refusal.jsx";
import Register, { Examine } from "./Register.jsx";
import RunColumn from "./RunColumn.jsx";
import Section from "./Section.jsx";
import Stages from "./Stages.jsx";
import screenConfig from "../config/screen.json";
import {
  answerDecision,
  finishReview,
  readExport,
  readProjects,
  readRun,
} from "./run_requests.js";

// The one status in which the server accepts an answer or a finished review.
const WAITING_FOR_REVIEW = "needs review";

// The screen's own name. The register it shows keeps the name the decisions and
// the exports give it; this is only what the person looking at it calls the
// thing, and it lives in one place so it can be changed in one place.
const PRODUCT_NAME = "Register";

export default function ReviewScreen({ runId: openedRunId }) {
  const [runId, setRunId] = useState(openedRunId ?? "");
  const [run, setRun] = useState(null);
  const [exported, setExported] = useState(null);
  // Two refusals, because they stop being true at different moments: a refused
  // read is answered by the next read that succeeds, while a refused answer
  // stands until another answer is sent. One shared value would either leave a
  // dead refusal beside confirmed data, or wipe a live one on the next poll.
  const [readRefusal, setReadRefusal] = useState(null);
  const [answerRefusal, setAnswerRefusal] = useState(null);
  const [answering, setAnswering] = useState(false);

  // The project list is its own read with its own refusal (L1): an
  // application that cannot list projects can still answer perfectly well
  // for the run being reviewed, and one refusal standing in for both would
  // hide that.
  const [projects, setProjects] = useState([]);
  const [projectsRoot, setProjectsRoot] = useState(null);
  const [availableFolders, setAvailableFolders] = useState([]);
  const [projectsRefusal, setProjectsRefusal] = useState(null);
  // Screen 10: before the first read comes back, "answered with nothing" and
  // "not asked yet" hold the same two values — an empty list and no refusal.
  // Only this boolean tells them apart, and it is set once and never reset,
  // so a later poll never brings the loading line back.
  const [projectsAnswered, setProjectsAnswered] = useState(false);
  // Screen 11: set only when a request never reached the application at all.
  // A confirmed refusal is not this — the application plainly answered.
  const [unreachable, setUnreachable] = useState(false);

  const [selectedProjectId, setSelectedProjectId] = useState(null);
  // Whether the right panel shows the project's own register rather than a
  // run. Mutually exclusive with `runId` being set — opening one always
  // clears the other, so the panel never mixes a run's decisions with the
  // project's register (section 2.3).
  const [registerOpen, setRegisterOpen] = useState(false);
  // "not read yet" and "read, and there is nothing" are two different
  // states: collapsing them made a project the server had already reported
  // as holding rows show an empty register until GET /export answered.
  const [registerRead, setRegisterRead] = useState(false);
  const [runsCollapsed, setRunsCollapsed] = useState(false);
  const [addProjectOpen, setAddProjectOpen] = useState(false);
  const [openSection, setOpenSection] = useState("stages");
  const readingPane = useScrollbarWhileScrolling();

  const readProjectsFromServer = useCallback(async () => {
    const answered = await readProjects();
    if (answered.unreachable) {
      // Screen 11: whatever this screen last read stays on it, unchanged.
      setUnreachable(true);
      return;
    }
    setUnreachable(false);
    setProjectsAnswered(true);
    if (!answered.ok) {
      setProjectsRefusal(answered.refusal);
      return;
    }
    projectsRef.current = answered.body.projects;
    setProjects(answered.body.projects);
    setProjectsRoot(answered.body.projects_root);
    setAvailableFolders(answered.body.available_folders);
    setProjectsRefusal(null);
  }, []);

  // A link to one run stays a link a reviewer can keep, so opening a run from
  // a column writes it into the address without adding a history entry.
  // What the last run said goes with it: until the new read answers, the
  // screen shows nothing rather than the previous run's decisions beside
  // buttons that already act on this one. Opening a run also closes the
  // register, the same clearing rule in the other direction.
  const openRun = useCallback((chosen) => {
    setRegisterOpen(false);
    setRunId(chosen);
    setRun(null);
    setExported(null);
    setReadRefusal(null);
    setAnswerRefusal(null);
    window.history.replaceState(null, "", `/ui/?run=${encodeURIComponent(chosen)}`);
  }, []);

  // The Register entry above a project's runs (section 2.3) opens that
  // project's register in the right panel — the same panel a run opens
  // into. It must clear whatever run was open, its export and both
  // refusals, the same way openRun clears the previous run: a previous
  // run's decisions must never sit beside the register.
  const openRegister = useCallback((projectId) => {
    setSelectedProjectId(projectId);
    setRegisterOpen(true);
    setRegisterRead(false);
    setRunId("");
    setRun(null);
    setExported(null);
    setReadRefusal(null);
    setAnswerRefusal(null);
    window.history.replaceState(null, "", "/ui/");
  }, []);

  // Choosing a project from the left column shows its runs in the middle one;
  // it does not itself open any run or the register, so nothing is shown that
  // a click has not actually asked for.
  const selectProject = useCallback((projectId) => {
    setSelectedProjectId(projectId);
    setRegisterOpen(false);
    setRunId("");
    setRun(null);
    setExported(null);
    setReadRefusal(null);
    window.history.replaceState(null, "", "/ui/");
  }, []);

  const readFromServer = useCallback(async () => {
    if (runId === "") {
      return;
    }
    const answered = await readRun(runId);
    if (answered.unreachable) {
      setUnreachable(true);
      return;
    }
    setUnreachable(false);
    if (!answered.ok) {
      setRun(null);
      setExported(null);
      setReadRefusal(answered.refusal);
      return;
    }
    setRun(answered.body);
    // The project this run belongs to is the server's own answer, so the
    // left and middle columns follow it rather than what was clicked.
    setSelectedProjectId(answered.body.project_id);
    setReadRefusal(null);
    if (!answered.body.exported) {
      setExported(null);
      return;
    }
    const register = await readExport(runId);
    if (register.unreachable) {
      setUnreachable(true);
      return;
    }
    setExported(register.ok ? register.body : null);
    if (!register.ok) {
      setReadRefusal(register.refusal);
    }
  }, [runId]);

  // No new endpoint and no new core function (section 2.2): the register a
  // project's panel shows is read the same two ways the screen already
  // reads everything else — GET /projects (already loaded, runs newest
  // first, each carrying row_count once it has exported) to find the most
  // recent run that has exported, then GET /runs/{id}/export for that run's
  // register.
  //
  // `projects` is read through a ref, updated on every render, rather than
  // closed over directly: `GET /projects` answers with a new array every
  // poll, and if this callback depended on `projects` itself it would be
  // rebuilt every poll too — the polling effect below depends on this
  // callback, so tearing it down and setting it up again would immediately
  // call `readProjectsFromServer()` again, which answers with yet another
  // new array, rebuilding the callback again. `registerOpen` and
  // `selectedProjectId` stay real dependencies: they are cheap primitives
  // that only change when a person navigates, so depending on them directly
  // is what makes opening the register (or switching project while it is
  // open) read it immediately, the same way `readFromServer` depending on
  // `runId` makes opening a run read immediately — without waiting for the
  // next poll tick.
  const projectsRef = useRef(projects);
  projectsRef.current = projects;

  const readRegisterFromServer = useCallback(async () => {
    if (!registerOpen) {
      return;
    }
    const project = projectsRef.current.find(
      (candidate) => candidate.project_id === selectedProjectId,
    );
    const latestExportedRun = project?.runs.find((run) => run.row_count !== null) ?? null;
    if (latestExportedRun === null) {
      setExported(null);
      setReadRefusal(null);
      setRegisterRead(true);
      return;
    }
    const register = await readExport(latestExportedRun.run_id);
    if (register.unreachable) {
      setUnreachable(true);
      return;
    }
    setUnreachable(false);
    setExported(register.ok ? register.body : null);
    setReadRefusal(register.ok ? null : register.refusal);
    setRegisterRead(true);
  }, [registerOpen, selectedProjectId]);

  useEffect(() => {
    // The register read depends on what GET /projects just said, so it waits
    // for that answer rather than reading the previous poll's snapshot and
    // showing a register one interval out of date.
    const readEverything = async () => {
      await readProjectsFromServer();
      readFromServer();
      readRegisterFromServer();
    };
    readEverything();
    const polling = setInterval(readEverything, screenConfig.poll_interval_ms);
    return () => clearInterval(polling);
  }, [readProjectsFromServer, readFromServer, readRegisterFromServer]);

  // Nothing the person clicked reaches the screen: the answer is sent, and what
  // is shown next is read back from the server that recorded it.
  // An action that never reached the application is screen 11's strip, not a
  // refusal: the application said nothing, so "the server refused" would put
  // words in the mouth of something that was not running.
  // Answers false when the request never landed, because there is then
  // nothing new to read back — and re-reading would clear the strip a moment
  // after raising it, leaving no sign that the click did nothing.
  const actionReachedTheApplication = useCallback((acted) => {
    if (acted.unreachable) {
      setUnreachable(true);
      setAnswerRefusal(null);
      return false;
    }
    setUnreachable(false);
    setAnswerRefusal(acted.ok ? null : acted.refusal);
    return true;
  }, []);

  const answer = useCallback(
    async (decisionId, outcome) => {
      setAnswering(true);
      const acted = await answerDecision(runId, decisionId, outcome);
      if (actionReachedTheApplication(acted)) {
        await readFromServer();
      }
      setAnswering(false);
    },
    [runId, readFromServer, actionReachedTheApplication],
  );

  const finish = useCallback(async () => {
    setAnswering(true);
    const finished = await finishReview(runId);
    if (actionReachedTheApplication(finished)) {
      await readFromServer();
    }
    setAnswering(false);
  }, [runId, readFromServer, actionReachedTheApplication]);

  // L5: nothing the person typed into the Add-project box reaches the screen.
  // The list is re-read and the run the server actually created is what gets
  // opened — never the id or the fields that were submitted.
  const startedRun = useCallback(
    async (startedRunId) => {
      await readProjectsFromServer();
      setAddProjectOpen(false);
      openRun(startedRunId);
    },
    [readProjectsFromServer, openRun],
  );

  // L5: only a run the server says is at review has work waiting. Decisions
  // left unanswered on a run that stopped can never be answered — counting
  // them would offer work the server refuses.
  const waiting =
    run === null || run.status !== WAITING_FOR_REVIEW
      ? 0
      : run.decisions.filter((decision) => decision.outcome === null).length;

  const selectedProject =
    projects.find((project) => project.project_id === selectedProjectId) ?? null;

  // A run panel has four tabs — Stages, Skipped, Decisions, Reported. The
  // register is not one of them: it is the project's own panel, opened from
  // the Register entry in the runs column, never from here (section 2.3).
  const sections =
    run === null
      ? []
      : [
          {
            id: "stages",
            number: "01",
            name: "Stages",
            tab: "Stages",
            body: <Stages run={run} />,
          },
          {
            id: "skipped",
            number: "02",
            name: "Skipped",
            tab: "Skipped",
            tabCount: run.skipped.length === 0 ? null : String(run.skipped.length),
            count: `${run.skipped.length} skipped`,
            body: <Skipped skipped={run.skipped} />,
          },
          {
            id: "decisions",
            number: "03",
            name: "Needs your decision",
            tab: "Decisions",
            tabCount: waiting === 0 ? null : String(waiting),
            tabWaiting: waiting > 0,
            body: (
              <Decisions
                decisions={run.decisions}
                examine={run.examine}
                reviewing={run.status === WAITING_FOR_REVIEW}
                answering={answering}
                waiting={waiting}
                onAnswer={answer}
                onFinish={finish}
              />
            ),
          },
          {
            id: "reported",
            number: "04",
            name: "Reported, not followed",
            tab: "Reported",
            tabCount:
              run.reported_instructions.length === 0
                ? null
                : String(run.reported_instructions.length),
            count: `${run.reported_instructions.length} reported`,
            body: <Reported reported={run.reported_instructions} />,
          },
        ];

  return (
    // The whole viewport, once. The header keeps its height, the unreachable
    // strip (when shown) sits directly under it, and everything below scrolls
    // in its own pane — a long register must never push the columns beside it
    // off the screen.
    <div className="flex h-screen flex-col overflow-hidden">
      <header className="flex h-14 shrink-0 items-center gap-3 bg-ink px-5 text-paper">
        <span className="block h-3 w-3 bg-signal" aria-hidden="true" />
        <h1 className="m-0 font-mono text-sm font-semibold tracking-tight">
          {PRODUCT_NAME}
        </h1>
      </header>

      {unreachable && (
        <p
          className="m-0 shrink-0 border-b-2 border-danger bg-card px-5 py-3 text-sm"
          role="alert"
        >
          <span className="eyebrow mb-1 block text-danger">
            Cannot reach the application
          </span>
          Check that Docker is running, then reload this page.
        </p>
      )}

      <div className="min-h-0 flex-1">
        {!projectsAnswered ? (
          <Loading />
        ) : (
          <div
            className={`grid h-full min-h-0 grid-cols-1 ${
              runsCollapsed
                ? "lg:grid-cols-[20rem_3rem_1fr]"
                : "lg:grid-cols-[20rem_13rem_1fr]"
            }`}
          >
            <ProjectList
              projects={projects}
              refusal={projectsRefusal}
              selectedProjectId={selectedProjectId}
              onSelectProject={selectProject}
              onOpenAddProject={() => setAddProjectOpen(true)}
            />

            <RunColumn
              project={selectedProject}
              selectedRunId={runId}
              registerOpen={registerOpen}
              onOpenRun={openRun}
              onOpenRegister={openRegister}
              collapsed={runsCollapsed}
              onToggleCollapse={() => setRunsCollapsed((was) => !was)}
            />

            <div className="grid min-h-0 min-w-0 grid-rows-[auto_1fr] bg-card">
              <div className="border-b border-line px-6 pt-7 pb-5 sm:px-10">
                <p className="eyebrow m-0">project</p>
                <p className="m-0 mt-1 text-2xl leading-tight font-semibold">
                  {selectedProject?.name ?? "This run"}
                </p>
                {!registerOpen && (
                  <SectionTabs
                    sections={sections}
                    openSection={openSection}
                    onOpenSection={setOpenSection}
                    disabled={run === null}
                  />
                )}
              </div>

              <main ref={readingPane} className="pane min-w-0 px-6 pt-8 pb-24 sm:px-10">
                {answerRefusal !== null && <Refusal text={answerRefusal} />}
                {readRefusal !== null && <Refusal text={readRefusal} />}

                {registerOpen ? (
                  <div className="max-w-5xl">
                    <ProjectRegisterSection exported={exported} read={registerRead} />
                  </div>
                ) : run === null ? (
                  <p className="max-w-prose text-ink-soft">
                    {projects.length === 0 && projectsRefusal === null
                      ? // Screen 1: no project exists yet anywhere.
                        "No runs yet — create a project first, then start its run."
                      : "Choose a run to see it here."}
                  </p>
                ) : (
                  <div className="max-w-5xl">
                    {sections.map(
                      (section) =>
                        section.id === openSection && (
                          <Section
                            key={section.id}
                            number={section.number}
                            name={section.name}
                            headingId={`${section.id}-heading`}
                            count={section.count}
                          >
                            {section.body}
                          </Section>
                        ),
                    )}
                  </div>
                )}
              </main>
            </div>
          </div>
        )}
      </div>

      {addProjectOpen && (
        <AddProject
          projectsRoot={projectsRoot}
          availableFolders={availableFolders}
          projects={projects}
          onStarted={startedRun}
          onClose={() => setAddProjectOpen(false)}
          onUnreachable={() => setUnreachable(true)}
        />
      )}
    </div>
  );
}

// Screen 10: exactly one of this or the columns, never both, never an empty
// column drawn in between.
function Loading() {
  return (
    <div className="flex h-full items-center justify-center">
      <p className="m-0 flex items-center gap-2 text-ink">
        <span className="inline-block h-2 w-2 bg-signal" aria-hidden="true" />
        Loading…
      </p>
    </div>
  );
}

// Tabs, not buttons: choosing which part of a run to read is navigation, and
// the only things on this screen that act on a run are Approve, Reject and
// Finish review.
function SectionTabs({ sections, openSection, onOpenSection, disabled }) {
  if (disabled) {
    return null;
  }
  return (
    <div
      role="tablist"
      aria-label="Sections of this run"
      className="mt-6 flex flex-wrap items-stretch gap-3"
    >
      {sections.map((section) => {
        const open = section.id === openSection;
        return (
          <button
            key={section.id}
            role="tab"
            type="button"
            aria-selected={open}
            aria-controls={`${section.id}-heading`}
            onClick={() => onOpenSection(section.id)}
            className={`flex items-center gap-2 border px-4 py-2 font-mono text-xs font-semibold tracking-wide whitespace-nowrap ${
              open
                ? "edge-shadow-sm border-signal-edge bg-signal text-ink"
                : "border-line text-ink-soft hover:border-line-strong hover:text-ink"
            }`}
          >
            {section.tab}
            {section.tabCount !== null && section.tabCount !== undefined && (
              <span
                className={`px-1.5 py-0.5 text-[11px] ${
                  section.tabWaiting
                    ? "border border-signal-edge bg-signal text-ink"
                    : "bg-line text-ink"
                }`}
              >
                {section.tabCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// Screen 5: the file name, then what happened — the `file`, `summary` and
// `reason` labels themselves are never printed. A dropped quote is told apart
// by carrying `summary` (a whole skipped document never does), so it shows
// its file, the requirement that was dropped, and why — never `quote`, which
// is the model's words, not the document's, and unverified besides.
function Skipped({ skipped }) {
  if (skipped.length === 0) {
    return <p className="m-0 text-ink-soft">This run skipped nothing.</p>;
  }
  return (
    <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2">
      {skipped.map((entry, place) => (
        <li key={place} className="border border-line bg-card px-4 py-3 text-sm">
          {entry.summary !== undefined ? (
            <p className="m-0">
              <span className="font-mono font-semibold">{entry.file}</span>
              <br />
              {entry.summary}
              <br />
              {entry.reason}
            </p>
          ) : entry.file !== undefined ? (
            <p className="m-0">
              <span className="font-mono font-semibold">{entry.file}</span>
              <br />
              {entry.reason}
            </p>
          ) : (
            <p className="m-0">{entry.reason}</p>
          )}
        </li>
      ))}
    </ul>
  );
}

function Reported({ reported }) {
  if (reported.length === 0) {
    return (
      <p className="m-0 text-ink-soft">
        No document in this run tried to give the system an instruction.
      </p>
    );
  }
  return (
    <>
      {/* Required, not decoration: without it a reader assumes the documents
          were discarded rather than read. It is said once above the cards
          rather than under each, and it stops there because an embedded
          instruction can appear on any document type, including one that
          states no requirement at all. */}
      <p className="m-0 mb-4 text-ink-soft">
        Reported, not followed. These documents were still read.
      </p>
      <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2">
        {reported.map((entry, place) => (
          <li key={place} className="border border-line bg-card px-4 py-3 text-sm">
            <p className="m-0">
              <span className="font-mono font-semibold">{entry.file}</span>
              <br />
              {entry.place}
            </p>
            <p className="m-0 mt-2 italic">{`"${entry.quote}"`}</p>
          </li>
        ))}
      </ul>
    </>
  );
}

function Decisions({
  decisions,
  examine,
  reviewing,
  answering,
  waiting,
  onAnswer,
  onFinish,
}) {
  return (
    <>
      {decisions.length === 0 ? (
        <p className="m-0 text-ink-soft">This run has raised no decision.</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {decisions.map((decision) => (
            <Question
              key={decision.decision_id}
              decision={decision}
              reviewing={reviewing}
              answering={answering}
              onAnswer={onAnswer}
            />
          ))}
        </ul>
      )}
      {examine !== null && (
        <div className="mt-8 border-t border-line pt-5">
          <Examine examine={examine} />
        </div>
      )}
      <FinishReview
        reviewing={reviewing}
        unanswered={waiting}
        answering={answering}
        onFinish={onFinish}
      />
    </>
  );
}

// Both rules belong to the server: it refuses a run that is not at review, and
// it refuses a review with an unanswered decision. The button is offered only
// where the run the server just described allows it.
function FinishReview({ reviewing, unanswered, answering, onFinish }) {
  if (!reviewing) {
    return (
      <p className="mt-8 text-sm text-ink-soft">
        This run is not at review, so nothing can be answered on it now.
      </p>
    );
  }
  if (unanswered > 0) {
    return (
      <p className="mt-8 text-sm text-ink-soft">
        Answer all {unanswered} to finish this review.
      </p>
    );
  }
  return (
    <button
      type="button"
      disabled={answering}
      onClick={onFinish}
      className="edge-shadow mt-8 border-2 border-signal-edge bg-signal px-6 py-3 font-mono text-sm font-semibold disabled:opacity-40"
    >
      Finish review
    </button>
  );
}

// The project's own panel (section 2.3): the same register component a run
// used to show under its own Register tab, reused here rather than
// duplicated. The empty state (section 2.4) covers a new project, a first
// run still working, and a run whose export was rejected — every case in
// which this project has never exported — with one line, never an empty
// table.
function ProjectRegisterSection({ exported, read }) {
  return (
    <Section
      number=""
      name="Register"
      headingId="project-register-heading"
      count={read && exported !== null ? `${exported.rows.length} rows` : null}
    >
      {!read ? (
        // Until the read answers this screen knows nothing about this
        // register, and saying it is empty would be a claim the server has
        // not made.
        <p className="m-0 max-w-prose text-sm text-ink-soft">
          Reading this register…
        </p>
      ) : exported === null ? (
        <p className="m-0 max-w-prose text-sm text-ink-soft">
          Nothing has been added to this register yet.
        </p>
      ) : (
        <Register exported={exported} />
      )}
    </Section>
  );
}
