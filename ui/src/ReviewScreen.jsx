import { useCallback, useEffect, useState } from "react";

import { useScrollbarWhileScrolling } from "./scrollbar_while_scrolling.js";

import AddProject from "./AddProject.jsx";
import ProjectList from "./ProjectList.jsx";
import Refusal from "./Refusal.jsx";
import RegisterPanel from "./RegisterPanel.jsx";
import ReportedInstructions from "./ReportedInstructions.jsx";
import RunColumn from "./RunColumn.jsx";
import RunTab from "./RunTab.jsx";
import Section from "./Section.jsx";
import Skipped from "./Skipped.jsx";
import screenConfig from "../config/screen.json";
import {
  answerDecision,
  finishReview,
  readHistory,
  readProjects,
  readRegister,
  readRun,
} from "./run_requests.js";

// The one status in which the server accepts an answer or a finished review.
const WAITING_FOR_REVIEW = "needs review";

// The decision the ending press writes. It is recorded, and it is shown
// nowhere as something to answer.
const EXPORT_GATE_KIND = "export";

const RUN_TAB = "run";

// The screen's own name. The register it shows keeps the name the decisions and
// the exports give it; this is only what the person looking at it calls the
// thing, and it lives in one place so it can be changed in one place.
const PRODUCT_NAME = "Register";

export default function ReviewScreen({ projectId: openedProjectId, runId: openedRunId }) {
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
  const [hasFilesByFolder, setHasFilesByFolder] = useState({});
  const [projectsRefusal, setProjectsRefusal] = useState(null);
  // Screen 10: before the first read comes back, "answered with nothing" and
  // "not asked yet" hold the same two values — an empty list and no refusal.
  // Only this boolean tells them apart, and it is set once and never reset,
  // so a later poll never brings the loading line back.
  const [projectsAnswered, setProjectsAnswered] = useState(false);
  // Screen 11: set only when a request never reached the application at all.
  // A confirmed refusal is not this — the application plainly answered.
  const [unreachable, setUnreachable] = useState(false);

  const [selectedProjectId, setSelectedProjectId] = useState(
    openedProjectId === "" ? null : (openedProjectId ?? null),
  );
  // A project named in the address alone still has to open its newest run
  // (item 49), and the run list only arrives with the first `GET /projects`.
  // Held until that read answers, then cleared, so a later poll never
  // re-opens a run the reader has since navigated away from.
  const [projectAwaitingItsRun, setProjectAwaitingItsRun] = useState(
    openedRunId ? null : (openedProjectId || null),
  );
  // Whether the right panel shows the project's own register rather than a
  // run. Mutually exclusive with `runId` being set — opening one always
  // clears the other, so the panel never mixes a run's decisions with the
  // project's register (section 2.3).
  const [registerOpen, setRegisterOpen] = useState(false);
  // "not read yet" and "read, and there is nothing" are two different
  // states: collapsing them made a project the server had already reported
  // as holding rows show an empty register until GET /export answered.
  const [registerRead, setRegisterRead] = useState(false);
  // The register's history, read beside the register and never inside it.
  // Null until the read answers: an empty list is the server saying this
  // register has no history, and "not asked yet" may not be shown as that.
  // Its refusal is its own for the reason the two above are: the history and
  // the register are read on the same poll, at the same time, so one shared
  // value would let either read wipe the other's live refusal.
  const [history, setHistory] = useState(null);
  const [historyRefusal, setHistoryRefusal] = useState(null);
  const [runsCollapsed, setRunsCollapsed] = useState(false);
  const [projectsCollapsed, setProjectsCollapsed] = useState(false);
  const [addProjectOpen, setAddProjectOpen] = useState(false);
  const [openSection, setOpenSection] = useState(RUN_TAB);
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
    setProjects(answered.body.projects);
    setProjectsRoot(answered.body.projects_root);
    setAvailableFolders(answered.body.available_folders);
    setHasFilesByFolder(answered.body.has_files_by_folder ?? {});
    setProjectsRefusal(null);
  }, []);

  // What the last run said goes with the run it belonged to: until the new
  // read answers, the screen shows nothing rather than the previous run's
  // decisions beside buttons that already act on this one. Opening a run also
  // closes the register, the same clearing rule in the other direction, and
  // comes back to the Run tab, which is where the waiting block lives (37).
  //
  // A click on the run that is already open does nothing at all: clearing the
  // run while its id stayed the same fired no re-read, so the panel sat on
  // "Choose a run to see it here." until the next poll (34).
  const openRun = useCallback(
    (chosen) => {
      if (chosen === runId && !registerOpen) {
        return;
      }
      setRegisterOpen(false);
      setRunId(chosen);
      setRun(null);
      setExported(null);
      setHistory(null);
      setHistoryRefusal(null);
      setReadRefusal(null);
      setAnswerRefusal(null);
      setOpenSection(RUN_TAB);
    },
    [runId, registerOpen],
  );

  // The Register entry above a project's runs (section 2.3) opens that
  // project's register in the right panel — the same panel a run opens
  // into. It must clear whatever run was open, its export and both
  // refusals, the same way openRun clears the previous run: a previous
  // run's decisions must never sit beside the register.
  const openRegister = useCallback((chosenProjectId) => {
    setSelectedProjectId(chosenProjectId);
    setProjectAwaitingItsRun(null);
    setRegisterOpen(true);
    setRegisterRead(false);
    setRunId("");
    setRun(null);
    setExported(null);
    setHistory(null);
    setHistoryRefusal(null);
    setReadRefusal(null);
    setAnswerRefusal(null);
  }, []);

  // Choosing a project from the left column opens its newest run at once
  // (item 49) — that is what a reader came to look at, and waiting for a
  // second click showed them an empty panel for no reason. A project that has
  // never run keeps the runs column's own empty line.
  const selectProject = useCallback(
    (chosenProjectId) => {
      const project = projects.find(
        (candidate) => candidate.project_id === chosenProjectId,
      );
      const newest = project?.runs[0] ?? null;
      setSelectedProjectId(chosenProjectId);
      setProjectAwaitingItsRun(null);
      setRegisterOpen(false);
      setRunId(newest === null ? "" : newest.run_id);
      setRun(null);
      setExported(null);
      setHistory(null);
      setHistoryRefusal(null);
      setReadRefusal(null);
      setOpenSection(RUN_TAB);
    },
    [projects],
  );

  // A project named in the address alone waits here for the run list to
  // arrive, and opens its newest run exactly once.
  useEffect(() => {
    if (projectAwaitingItsRun === null) {
      return;
    }
    const project = projects.find(
      (candidate) => candidate.project_id === projectAwaitingItsRun,
    );
    if (project === undefined) {
      return;
    }
    setProjectAwaitingItsRun(null);
    if (project.runs.length > 0) {
      setRunId(project.runs[0].run_id);
    }
  }, [projectAwaitingItsRun, projects]);

  // One writer for the address, so a link a reviewer keeps always names what
  // is actually on screen (items 9 / S18). The project is written as soon as
  // it is known — for a run opened by id alone that is the server's own
  // answer, not something the address had to carry.
  useEffect(() => {
    const named = [];
    if (selectedProjectId !== null) {
      named.push(`project=${encodeURIComponent(selectedProjectId)}`);
    }
    if (runId !== "") {
      named.push(`run=${encodeURIComponent(runId)}`);
    }
    window.history.replaceState(
      null,
      "",
      named.length === 0 ? "/ui/" : `/ui/?${named.join("&")}`,
    );
  }, [selectedProjectId, runId]);

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
  }, [runId]);

  // The register is the project's own reading, served live from its
  // committed rows by one route — GET /projects/{id}/register. There is no
  // walk over the project's runs any more: no run sits between the panel
  // and the register it shows.
  const readRegisterFromServer = useCallback(async () => {
    if (!registerOpen) {
      return;
    }
    const register = await readRegister(selectedProjectId);
    if (register.unreachable) {
      setUnreachable(true);
      return;
    }
    setUnreachable(false);
    setExported(register.ok ? register.body : null);
    setReadRefusal(register.ok ? null : register.refusal);
    setRegisterRead(true);
  }, [registerOpen, selectedProjectId]);

  // The same trigger and the same refresh the register read has, into state of
  // its own — the ordering and the wording of every entry are the core
  // function's, so this only carries what it answered.
  const readHistoryFromServer = useCallback(async () => {
    if (!registerOpen) {
      return;
    }
    const answered = await readHistory(selectedProjectId);
    if (answered.unreachable) {
      setUnreachable(true);
      return;
    }
    setUnreachable(false);
    setHistory(answered.ok ? answered.body : null);
    setHistoryRefusal(answered.ok ? null : answered.refusal);
  }, [registerOpen, selectedProjectId]);

  useEffect(() => {
    const readEverything = () => {
      readProjectsFromServer();
      readFromServer();
      readRegisterFromServer();
      readHistoryFromServer();
    };
    readEverything();
    const polling = setInterval(readEverything, screenConfig.poll_interval_ms);
    return () => clearInterval(polling);
  }, [
    readProjectsFromServer,
    readFromServer,
    readRegisterFromServer,
    readHistoryFromServer,
  ]);

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

  // One press ends the review and carries the answer with it, so this is
  // called with what the pressed button means, never with nothing.
  const finish = useCallback(
    async (addToRegister) => {
      setAnswering(true);
      const finished = await finishReview(runId, addToRegister);
      if (actionReachedTheApplication(finished)) {
        await readFromServer();
      }
      setAnswering(false);
    },
    [runId, readFromServer, actionReachedTheApplication],
  );

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

  // An empty folder makes a project and starts no run (locked change (a)):
  // the new project is selected, no run is opened, and the address carries
  // the project alone.
  const createdProject = useCallback(
    async (createdProjectId) => {
      await readProjectsFromServer();
      setAddProjectOpen(false);
      setSelectedProjectId(createdProjectId);
      setProjectAwaitingItsRun(null);
      setRegisterOpen(false);
      setRunId("");
      setRun(null);
    },
    [readProjectsFromServer],
  );

  // The gate is not a question anybody is asked: it is written when one of
  // the two ending buttons is pressed, and the run then carries it answered.
  // Filtered here, once, so the count and the cards can never disagree.
  const questions =
    run === null
      ? []
      : run.decisions.filter((decision) => decision.kind !== EXPORT_GATE_KIND);

  // L5: only a run the server says is at review has work waiting. Decisions
  // left unanswered on a run that stopped can never be answered — counting
  // them would offer work the server refuses.
  const waiting =
    run === null || run.status !== WAITING_FOR_REVIEW
      ? 0
      : questions.filter((decision) => decision.outcome === null).length;

  const selectedProject =
    projects.find((project) => project.project_id === selectedProjectId) ?? null;

  // A run panel has three tabs (item 12). The register is not one of them: it
  // is the project's own panel, opened from the Register entry in the runs
  // column, never from here (section 2.3).
  const sections =
    run === null
      ? []
      : [
          {
            id: RUN_TAB,
            name: "Run",
            tab: "Run",
            tabCount: waiting === 0 ? null : String(waiting),
            tabWaiting: waiting > 0,
            body: (
              <RunTab
                run={run}
                decisions={questions}
                waiting={waiting}
                answering={answering}
                onAnswer={answer}
                onFinish={finish}
              />
            ),
          },
          {
            id: "skipped",
            name: "Skipped",
            tab: "Skipped",
            tabCount: run.skipped.length === 0 ? null : String(run.skipped.length),
            count:
              run.skipped.length === 0 ? null : `${run.skipped.length} skipped`,
            body: <Skipped entries={run.skipped} />,
          },
          {
            id: "reported",
            name: "Reported instructions",
            tab: "Reported instructions",
            tabCount:
              run.reported_instructions.length === 0
                ? null
                : String(run.reported_instructions.length),
            count:
              run.reported_instructions.length === 0
                ? null
                : `${run.reported_instructions.length} reported`,
            body: <ReportedInstructions reported={run.reported_instructions} />,
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
            className={`grid h-full min-h-0 grid-cols-1 ${columnWidths(
              projectsCollapsed,
              runsCollapsed,
            )}`}
          >
            <ProjectList
              projects={projects}
              refusal={projectsRefusal}
              selectedProjectId={selectedProjectId}
              collapsed={projectsCollapsed}
              onToggleCollapse={() => setProjectsCollapsed((was) => !was)}
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
                {!registerOpen && run !== null && (
                  <SectionTabs
                    sections={sections}
                    openSection={openSection}
                    onOpenSection={setOpenSection}
                  />
                )}
              </div>

              <main ref={readingPane} className="pane min-w-0 px-6 pt-8 pb-24 sm:px-10">
                {answerRefusal !== null && <Refusal text={answerRefusal} />}
                {readRefusal !== null && <Refusal text={readRefusal} />}
                {historyRefusal !== null && <Refusal text={historyRefusal} />}

                {registerOpen ? (
                  <div className="max-w-5xl">
                    <RegisterPanel
                      exported={exported}
                      read={registerRead}
                      history={history}
                    />
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
          hasFilesByFolder={hasFilesByFolder}
          projects={projects}
          onStarted={startedRun}
          onCreated={createdProject}
          onClose={() => setAddProjectOpen(false)}
          onUnreachable={() => setUnreachable(true)}
        />
      )}
    </div>
  );
}

// Written out whole rather than assembled, because Tailwind reads these class
// names out of this file: a string built at run time is a class that was
// never generated. Either column collapses to a 3rem rail, and the reading
// pane takes back what they gave up (items 3, 19).
function columnWidths(projectsCollapsed, runsCollapsed) {
  if (projectsCollapsed) {
    return runsCollapsed
      ? "lg:grid-cols-[3rem_3rem_1fr]"
      : "lg:grid-cols-[3rem_12rem_1fr]";
  }
  return runsCollapsed
    ? "lg:grid-cols-[13rem_3rem_1fr]"
    : "lg:grid-cols-[13rem_12rem_1fr]";
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
// the two buttons that end the review.
function SectionTabs({ sections, openSection, onOpenSection }) {
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
            className={`flex cursor-pointer items-center gap-2 border px-4 py-2 font-mono text-xs font-semibold tracking-wide whitespace-nowrap active:translate-y-px ${
              open
                ? "edge-shadow-sm border-signal-edge bg-signal text-ink"
                : "border-line text-ink-soft hover:border-line-strong hover:bg-paper hover:text-ink"
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
