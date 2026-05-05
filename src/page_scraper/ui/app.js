const form = document.querySelector("#scrape-form");
const urls = document.querySelector("#urls");
const statusBox = document.querySelector(".status");
const statusTitle = document.querySelector("#status-title");
const statusCopy = document.querySelector("#status-copy");
const results = document.querySelector("#results");
const resultList = document.querySelector("#result-list");
const details = document.querySelector("#details");
const detailOutput = document.querySelector("#detail-output");
const buttons = Array.from(document.querySelectorAll("button"));

function setBusy(isBusy) {
  buttons.forEach((button) => {
    button.disabled = isBusy;
  });
}

function setStatus(title, copy, state = "normal") {
  statusTitle.textContent = title;
  statusCopy.textContent = copy;
  statusBox.dataset.state = state;
}

function showDetails(payload) {
  details.hidden = false;
  detailOutput.textContent = JSON.stringify(payload, null, 2);
}

function renderSavedPages(saved) {
  resultList.innerHTML = "";
  saved.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item.ok && item.saved_folder ? `data/pages/${item.saved_folder}` : `${item.url} could not be saved`;
    resultList.appendChild(li);
  });
  results.hidden = saved.length === 0;
}

async function postJson(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw data;
  }
  return data;
}

async function pollJob(jobId, runningCopy) {
  setBusy(true);
  setStatus(runningCopy, "This can take a few moments.");

  while (true) {
    const response = await fetch(`/api/jobs/${jobId}`);
    const job = await response.json();
    const lastMessage = job.messages?.at(-1);
    if (lastMessage) {
      setStatus(runningCopy, lastMessage);
    }

    if (job.status === "done") {
      setBusy(false);
      showDetails(job);
      return job;
    }

    if (job.status === "error") {
      setBusy(false);
      showDetails(job);
      setStatus("Some pages could not be saved", job.error || "Something went wrong.", "error");
      return job;
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  results.hidden = true;
  details.hidden = true;

  try {
    const start = await postJson("/api/scrape", { urlsText: urls.value });
    const job = await pollJob(start.jobId, "Saving pages...");
    const saved = job.result?.saved || [];
    renderSavedPages(saved);
    const failedCount = saved.filter((item) => !item.ok).length;
    if (failedCount > 0) {
      setStatus("Some pages could not be saved", `${saved.length - failedCount} saved, ${failedCount} need attention.`, "error");
    } else {
      setStatus("Saved pages", `${saved.length} page folder${saved.length === 1 ? "" : "s"} saved.`);
    }
  } catch (error) {
    setBusy(false);
    showDetails(error);
    setStatus("Some pages could not be saved", error.error || "Check the links and try again.", "error");
  }
});

document.querySelectorAll("[data-build]").forEach((button) => {
  button.addEventListener("click", async () => {
    const type = button.dataset.build;
    const label = "content files";
    results.hidden = true;
    details.hidden = true;

    try {
      const start = await postJson(`/api/build/${type}`);
      const job = await pollJob(start.jobId, `Building ${label}...`);
      if (job.status === "done") {
        const rebuilt = job.result?.rebuilt?.length || 0;
        setStatus("Content files are ready", `${rebuilt} page folder${rebuilt === 1 ? "" : "s"} refreshed.`);
      }
    } catch (error) {
      setBusy(false);
      showDetails(error);
      setStatus(`Could not build ${label}`, error.error || "Something went wrong.", "error");
    }
  });
});
