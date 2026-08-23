// Items 22/30/42, 27, 32 and the S21 split. Every sentence on a decision card
// is one the backend wrote and froze into `question`; the screen lays the
// blocks out and adds no wording. The fixtures here are the payload shapes
// `app/review/decision_text.py` actually builds — the whole text and the parts
// beside it, written out separately, so a screen that rebuilt one from the
// other could not pass.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  decisionReply,
  findingDecisionReply,
  observationMatchReply,
  projectsReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

function screenShowing(decisions, answering) {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: () => ({ body: runReply({ decisions: answering ?? decisions }) }),
      },
      {
        method: "POST",
        path: `/runs/${runId}/decisions`,
        reply: { body: {} },
      },
    ]),
  );
  render(<ReviewScreen projectId="" runId={runId} />);
}

async function cardFor(anchor) {
  return (await screen.findByText(anchor)).closest("li");
}

// Every run of text the card shows, with the layout's own gaps closed up, so
// a sentence the screen invented would show up as a run of words the stored
// text does not hold.
function sentencesOf(card) {
  return [...card.querySelectorAll("p, dd, dt")]
    .map((part) => part.textContent.trim())
    .filter((text) => text.length > 0);
}

test("a possible match shows the row, the quote, the question and both answers", async () => {
  const decision = decisionReply();
  screenShowing([decision]);
  const card = await cardFor("Is this the same ask as row 2?");

  expect(card.textContent).toContain(decision.row.label);
  for (const [heading, value] of Object.entries(decision.row.cells)) {
    expect(card.textContent).toContain(heading);
    expect(card.textContent).toContain(value);
  }
  expect(card.textContent).toContain(decision.quotes[0].source_line);
  expect(card.textContent).toContain(decision.quotes[0].quote);
  expect(card.textContent).toContain("Row 2 changes: Written down: Yes");
  expect(card.textContent).toContain(decision.if_rejected);
});

test("two observations about one row are two blocks under one question", async () => {
  const decision = observationMatchReply();
  screenShowing([decision]);
  const card = await cardFor("Is this about row 2?");

  for (const quote of decision.quotes) {
    expect(within(card).getByText(`"${quote.quote}"`)).toBeTruthy();
  }
  // One question, not one per quote.
  expect(within(card).getAllByText("Is this about row 2?")).toHaveLength(1);
});

test("a finding shows the rule and the model's issue line and no quote block", async () => {
  const decision = findingDecisionReply();
  screenShowing([decision]);
  const card = await cardFor("Does row 4 break this rule?");

  expect(card.textContent).toContain(`Rule: ${decision.rule_text}`);
  expect(card.textContent).toContain(decision.issue);
  expect(card.textContent).toContain("The finding is added to row 4.");
  expect(card.textContent).toContain(decision.if_rejected);
  expect(card.querySelectorAll("blockquote")).toHaveLength(0);
});

test("every sentence the card shows is one the stored text holds", async () => {
  for (const decision of [
    decisionReply(),
    observationMatchReply(),
    findingDecisionReply(),
  ]) {
    const stored = decision.question;
    const built = new Set(
      // The kind, the answered/unanswered mark and the two button words are
      // the screen's own labels; every other run of text must be the
      // server's.
      ["unanswered", decision.kind, "Approve", "Reject"],
    );
    screenShowing([decision]);
    const card = await cardFor(decision.question.split("\n\n").at(-2));
    for (const sentence of sentencesOf(card)) {
      if (built.has(sentence)) {
        continue;
      }
      expect(stored).toContain(sentence);
    }
    vi.unstubAllGlobals();
    screen.getByRole("banner").remove();
  }
});

test("no card writes a hash in front of a row number", async () => {
  screenShowing([decisionReply(), observationMatchReply(), findingDecisionReply()]);
  await cardFor("Is this about row 2?");

  expect(document.body.textContent).not.toMatch(/#\d/);
});

test("the accent moves to whichever answer the server has recorded", async () => {
  // The server is the only thing that decides which answer stands, so it
  // answers `approved` until the reject is posted and `rejected` after.
  let recorded = "approved";
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: () => ({
          body: runReply({ decisions: [decisionReply({ outcome: recorded })] }),
        }),
      },
      {
        method: "POST",
        path: `/runs/${runId}/decisions`,
        reply: () => {
          recorded = "rejected";
          return { body: {} };
        },
      },
    ]),
  );
  render(<ReviewScreen projectId="" runId={runId} />);
  const card = await cardFor("Is this the same ask as row 2?");

  const approve = within(card).getByRole("button", { name: "Approve" });
  const reject = within(card).getByRole("button", { name: "Reject" });
  expect(approve.className).toContain("bg-signal");
  expect(reject.className).not.toContain("bg-signal");
  // The other answer stays live: an answer may be changed until the review is
  // finished, so the screen never closes a window the server leaves open.
  expect(reject.disabled).toBe(false);

  fireEvent.click(reject);
  await waitFor(() => {
    expect(
      within(card).getByRole("button", { name: "Reject" }).className,
    ).toContain("bg-signal");
  });
  expect(
    within(card).getByRole("button", { name: "Approve" }).className,
  ).not.toContain("bg-signal");
});

test("both answers and their consequence text share one grid", async () => {
  screenShowing([observationMatchReply()]);
  const card = await cardFor("Is this about row 2?");

  // One grid means a label and the sentence beside it cannot start at
  // different places, at any width (item 32).
  const answers = card.querySelector(":scope > dl.decision-lines");
  const labels = [...answers.children].filter((part) => part.tagName === "DT");
  const consequences = [...answers.children].filter((part) => part.tagName === "DD");
  expect(labels.map((label) => label.textContent)).toEqual(["Approve", "Reject"]);
  expect(consequences).toHaveLength(2);
});
