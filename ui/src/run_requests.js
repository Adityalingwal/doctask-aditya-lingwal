// The screen is served by the application it talks to, so every request is
// same-origin and no host, key or token is configured anywhere in this folder.
const JSON_FORMAT = "json";

export async function readRuns() {
  return await ask("GET", "/runs");
}

export async function createProject(name, sourceFolderPath) {
  return await ask("POST", "/projects", {
    name,
    source_folder_path: sourceFolderPath,
  });
}

export async function startRun(projectId) {
  return await ask("POST", "/runs", { project_id: projectId });
}

export async function readRun(runId) {
  return await ask("GET", `/runs/${encodeURIComponent(runId)}`);
}

export async function readExport(runId) {
  return await ask(
    "GET",
    `/runs/${encodeURIComponent(runId)}/export?format=${JSON_FORMAT}`,
  );
}

export async function answerDecision(runId, decisionId, outcome) {
  return await ask("POST", `/runs/${encodeURIComponent(runId)}/decisions`, {
    decision_id: decisionId,
    outcome,
  });
}

export async function finishReview(runId) {
  return await ask("POST", `/runs/${encodeURIComponent(runId)}/finish-review`);
}

/** One request, answered as either the server's body or the server's refusal. */
async function ask(method, path, payload) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: payload === undefined ? {} : { "Content-Type": "application/json" },
      body: payload === undefined ? undefined : JSON.stringify(payload),
    });
  } catch (unreachable) {
    return {
      ok: false,
      refusal:
        `${method} ${path} did not reach the application (${unreachable.message}) `
        + "— check that `docker compose up` is still running and reload this page.",
    };
  }
  const body = await response.json();
  if (!response.ok) {
    // The refusal a core function wrote already names the cause and the fix;
    // rewriting it here would put a second, weaker sentence in front of it.
    return { ok: false, refusal: body.detail ?? `${method} ${path} answered ${response.status}.` };
  }
  return { ok: true, body };
}
