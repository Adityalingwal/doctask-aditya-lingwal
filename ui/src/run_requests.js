// The screen is served by the application it talks to, so every request is
// same-origin and no host, key or token is configured anywhere in this folder.
const JSON_FORMAT = "json";

export async function readProjects() {
  return await ask("GET", "/projects");
}

export async function createProject(sourceFolderPath) {
  return await ask("POST", "/projects", {
    source_folder_path: sourceFolderPath,
  });
}

export async function startRun(projectId) {
  return await ask("POST", "/runs", { project_id: projectId });
}

export async function readRun(runId) {
  return await ask("GET", `/runs/${encodeURIComponent(runId)}`);
}

export async function readRegister(projectId) {
  return await ask(
    "GET",
    `/projects/${encodeURIComponent(projectId)}/register?format=${JSON_FORMAT}`,
  );
}

// The register's own history, a read of its own: it is deliberately not part
// of the register document, so it is asked for separately and carries no
// format parameter.
export async function readHistory(projectId) {
  return await ask("GET", `/projects/${encodeURIComponent(projectId)}/history`);
}

export async function answerDecision(runId, decisionId, outcome) {
  return await ask("POST", `/runs/${encodeURIComponent(runId)}/decisions`, {
    decision_id: decisionId,
    outcome,
  });
}

export async function finishReview(runId, addToRegister) {
  return await ask("POST", `/runs/${encodeURIComponent(runId)}/finish-review`, {
    add_to_register: addToRegister,
  });
}

/**
 * One request, answered as either the server's body or a refusal. `unreachable`
 * is true only when the request never reached the application at all (screen
 * 11) — a real answer the server sent back, refusal or not, is never marked
 * this way, because the application plainly is reachable in that case.
 */
async function ask(method, path, payload) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: payload === undefined ? {} : { "Content-Type": "application/json" },
      body: payload === undefined ? undefined : JSON.stringify(payload),
    });
  } catch {
    return {
      ok: false,
      unreachable: true,
      refusal:
        "Check that Docker is running, then reload this page.",
    };
  }
  const body = await response.json();
  if (!response.ok) {
    const detail = body.detail;
    if (detail === undefined) {
      return { ok: false, refusal: `${method} ${path} answered ${response.status}.` };
    }
    if (typeof detail === "string") {
      // The refusal a core function wrote already names the cause and the
      // fix; rewriting it here would put a second, weaker sentence in front
      // of it.
      return { ok: false, refusal: detail };
    }
    // FastAPI's own validation error sends `detail` as a list of objects,
    // which this screen cannot render as a sentence. The whole body still
    // reaches the console, so the actual cause is not lost — only kept off
    // the screen a caller who is not a developer would be reading.
    console.error("The application refused this request with a body this screen cannot read:", body);
    return { ok: false, refusal: "The application did not accept this request." };
  }
  return { ok: true, body };
}
