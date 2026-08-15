import { useCallback, useEffect, useState } from "react";

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
    setProjects(answered.body.projects);
    setProjectsRoot(answered.body.projects_root);
    setAvailableFolders(answered.body.available_folders);
    setProjectsRefusal(null);
  }, []);

  // A link to one run stays a link a reviewer can keep, so opening a run from
  // a column writes it into the address without adding a history entry.
  const openRun = useCallback((chosen) => {
    setRunId(chosen);
    window.history.replaceState(null, "", `/ui/?run=${encodeURIComponent(chosen)}`);
  }, []);

  // Choosing a project from the left column shows its runs in the middle one;
  // it does not itself open any run, so nothing is shown that a click on a
  // run row has not actually asked for.
  const selectProject = useCallback((projectId) => {
    setSelectedProjectId(projectId);
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

  useEffect(() => {
    readProjectsFromServer();
    readFromServer();
    const polling = setInterval(() => {
      readProjectsFromServer();
      readFromServer();
    }, screenConfig.poll_interval_ms);
    return () => clearInterval(polling);
  }, [readProjectsFromServer, readFromServer]);

  // Nothing the person clicked reaches the screen: the answer is sent, and what
  // is shown next is read back from the server that recorded it.
  const answer = useCallback(
    async (decisionId, outcome) => {
      setAnswering(true);
      const answered = await answerDecision(runId, decisionId, outcome);
      setAnswerRefusal(answered.ok ? null : answered.refusal);
      await readFromServer();
      setAnswering(false);
    },
    [runId, readFromServer],
  );

  const finish = useCallback(async () => {
    setAnswering(true);
    const finished = await finishReview(runId);
    setAnswerRefusal(finished.ok ? null : finished.refusal);
    await readFromServer();
    setAnswering(false);
  }, [runId, readFromServer]);

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

  const waiting =
    run === null
      ? 0
      : run.decisions.filter((decision) => decision.outcome === null).length;

  const selectedProject =
    projects.find((project) => project.project_id === selectedProjectId) ?? null;

  // The five sections and their order are fixed; what changes here is that one
  // is read at a time, so a register of forty rows never buries the timings
  // under it.
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
            id: "register",
            number: "04",
            name: "Register",
            tab: "Register",
            tabCount: exported === null ? null : String(exported.rows.length),
            count: exported === null ? null : `${exported.rows.length} rows`,
            body: <RegisterSection exported={exported} />,
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
              onOpenRun={openRun}
              collapsed={runsCollapsed}
              onToggleCollapse={() => setRunsCollapsed((was) => !was)}
            />

            <div className="grid min-h-0 min-w-0 grid-rows-[auto_1fr] bg-card">
              <div className="border-b border-line px-6 pt-7 pb-5 sm:px-10">
                <p className="eyebrow m-0">project</p>
                <p className="m-0 mt-1 text-2xl leading-tight font-semibold">
                  {selectedProject?.name ?? "This run"}
                </p>
                <SectionTabs
                  sections={sections}
                  openSection={openSection}
                  onOpenSection={setOpenSection}
                  disabled={run === null}
                />
              </div>

              <main ref={readingPane} className="pane min-w-0 px-6 pt-8 pb-24 sm:px-10">
                {answerRefusal !== null && <Refusal text={answerRefusal} />}
                {readRefusal !== null && <Refusal text={readRefusal} />}

                {run === null ? (
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
          onStarted={startedRun}
          onClose={() => setAddProjectOpen(false)}
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
      <p className="m-0 flex items-center gap-2 text-ink-soft">
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

// Screen 5: the file name, then the sentence — the `file` and `reason`
// labels themselves are never printed. A dropped quote carries no file name
// (it is part of one already read), so it prints its sentence alone.
function Skipped({ skipped }) {
  if (skipped.length === 0) {
    return <p className="m-0 text-ink-soft">This run skipped nothing.</p>;
  }
  return (
    <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2">
      {skipped.map((entry, place) => (
        <li key={place} className="border border-line bg-card px-4 py-3 text-sm">
          {entry.file !== undefined ? (
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

function RegisterSection({ exported }) {
  if (exported === null) {
    return (
      <p className="m-0 max-w-prose text-sm text-ink-soft">
        Nothing exported yet. The register appears here once the export is
        approved.
      </p>
    );
  }
  return <Register exported={exported} />;
}
