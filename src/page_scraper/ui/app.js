const form = document.querySelector("#scrape-form");
const urls = document.querySelector("#urls");
const statusBox = document.querySelector(".status");
const statusTitle = document.querySelector("#status-title");
const statusCopy = document.querySelector("#status-copy");
const results = document.querySelector("#results");
const resultList = document.querySelector("#result-list");
const discoveryResults = document.querySelector("#discovery-results");
const assetList = document.querySelector("#asset-list");
const details = document.querySelector("#details");
const detailOutput = document.querySelector("#detail-output");
const startUrl = document.querySelector("#start-url");
const maxDepth = document.querySelector("#max-depth");
const sameDomain = document.querySelector("#same-domain");
const startPath = document.querySelector("#start-path");
const includeImages = document.querySelector("#include-images");
const includeDocuments = document.querySelector("#include-documents");
const discIndicator = document.querySelector("#disc-indicator");
const linksFound = document.querySelector("#links-found");
const discoverButton = document.querySelector("#discover");
const downloadButton = document.querySelector("#download");
const crawlControls = document.querySelector("#crawl-controls");
const pauseButton = document.querySelector("#pause");
const resumeButton = document.querySelector("#resume");
const cancelButton = document.querySelector("#cancel");
const saveButton = form.querySelector("button[type='submit']");
const refreshButtons = Array.from(document.querySelectorAll("[data-build]"));

let activeJobId = null;
let activePages = [];
let activeAssets = [];

function isTerminalStatus(status) {
  return ["done", "completed", "completed_with_errors", "ready", "cancelled", "paused"].includes(status);
}

function setBusy(isBusy) {
  saveButton.disabled = isBusy;
  refreshButtons.forEach((button) => {
    button.disabled = isBusy;
  });
  discoverButton.disabled = isBusy;
  downloadButton.disabled = isBusy || activeJobId === null || activePages.length === 0;
}

function setCrawlControls(visible) {
  crawlControls.hidden = !visible;
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

function hideDetails() {
  details.hidden = true;
  detailOutput.textContent = "";
}

function setLinksFound(count) {
  linksFound.textContent = String(count);
}

function pageUrl(page) {
  return page.url || page.final_url || page.normalized_url || "";
}

function updateUrlBox(pages) {
  const pageLinks = pages.map(pageUrl).filter(Boolean);
  urls.value = pageLinks.join("\n");
  setLinksFound(pageLinks.length);
}

function selectedTextareaUrls() {
  return new Set(
    urls.value
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean),
  );
}

function renderSavedPages(saved) {
  resultList.innerHTML = "";
  saved.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item.ok && item.files?.source_html ? item.files.source_html : `${item.url} could not be saved`;
    resultList.appendChild(li);
  });
  results.hidden = saved.length === 0;
}

function renderAssetTable(assets) {
  assetList.innerHTML = "";
  assets.forEach((asset) => {
    const row = document.createElement("tr");

    const saveCell = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = asset.selected !== false;
    checkbox.dataset.assetId = asset.id;
    checkbox.addEventListener("change", async () => {
      if (!activeJobId) {
        return;
      }
      await patchJson(`/api/jobs/${activeJobId}/assets/selection`, {
        ids: [asset.id],
        selected: checkbox.checked,
      });
      asset.selected = checkbox.checked;
    });
    saveCell.appendChild(checkbox);

    const typeCell = document.createElement("td");
    typeCell.textContent = asset.asset_type || "file";

    const urlCell = document.createElement("td");
    urlCell.className = "url-cell";
    urlCell.textContent = asset.url;

    row.append(saveCell, typeCell, urlCell);
    assetList.appendChild(row);
  });

  discoveryResults.hidden = assets.length === 0;
}

function updateDiscoveryView(job) {
  activePages = job.pages || [];
  activeAssets = job.assets || [];
  updateUrlBox(activePages);
  renderAssetTable(activeAssets);
  downloadButton.hidden = activePages.length === 0 && activeAssets.length === 0;
  downloadButton.disabled = !isTerminalStatus(job.status) || (activePages.length === 0 && activeAssets.length === 0);
}

async function postJson(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await readJsonResponse(response);
  if (!response.ok) {
    throw data;
  }
  return data;
}

async function patchJson(url, payload = {}) {
  const response = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await readJsonResponse(response);
  if (!response.ok) {
    throw data;
  }
  return data;
}

async function getJson(url) {
  const response = await fetch(url);
  const data = await readJsonResponse(response);
  if (!response.ok) {
    throw data;
  }
  return data;
}

async function readJsonResponse(response) {
  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  const text = await response.text();
  return {
    error: response.status === 404
      ? "This browser window is talking to an older app server. Restart the local Page Saver server and refresh the page."
      : "The app server returned a response the browser could not understand.",
    status: response.status,
    body: text.slice(0, 500),
  };
}

async function pollJob(jobId, runningCopy, onUpdate = null) {
  setBusy(true);
  setStatus(runningCopy, "This can take a few moments.");

  while (true) {
    const job = await getJson(`/api/jobs/${jobId}`);
    if (onUpdate) {
      onUpdate(job);
    }
    const lastMessage = job.messages?.at(-1) || job.events?.at(-1)?.message;
    if (lastMessage) {
      setStatus(runningCopy, lastMessage);
    }

    if (isTerminalStatus(job.status)) {
      setBusy(false);
      showDetails(job);
      return job;
    }

    if (job.status === "error" || job.status === "failed") {
      setBusy(false);
      showDetails(job);
      setStatus("Something needs attention", job.error || "The job could not finish.", "error");
      return job;
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

async function syncPageSelectionFromTextbox() {
  if (!activeJobId || activePages.length === 0) {
    return;
  }

  const chosenUrls = selectedTextareaUrls();
  const allPageIds = activePages.map((page) => page.id);
  const chosenPageIds = activePages
    .filter((page) => chosenUrls.has(pageUrl(page)))
    .map((page) => page.id);

  if (allPageIds.length > 0) {
    await patchJson(`/api/jobs/${activeJobId}/pages/selection`, {
      ids: allPageIds,
      selected: false,
    });
  }
  if (chosenPageIds.length > 0) {
    await patchJson(`/api/jobs/${activeJobId}/pages/selection`, {
      ids: chosenPageIds,
      selected: true,
    });
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  results.hidden = true;
  hideDetails();

  try {
    const start = await postJson("/api/scrape", { urlsText: urls.value });
    const job = await pollJob(start.jobId, "Saving pages...");
    const saved = job.result?.saved || [];
    renderSavedPages(saved);
    const failedCount = saved.filter((item) => !item.ok).length;
    if (failedCount > 0) {
      setStatus("Some pages could not be saved", `${saved.length - failedCount} saved, ${failedCount} need attention.`, "error");
    } else {
      setStatus("Saved pages", `${saved.length} page folder${saved.length === 1 ? "" : "s"} saved under ${job.result?.output_root || "data/jobs"}.`);
    }
  } catch (error) {
    setBusy(false);
    showDetails(error);
    setStatus("Some pages could not be saved", error.error || "Check the links and try again.", "error");
  }
});

refreshButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    results.hidden = true;
    hideDetails();
    try {
      const start = await postJson(`/api/build/${button.dataset.build}`);
      const job = await pollJob(start.jobId, "Refreshing content files...");
      const rebuilt = job.result?.rebuilt?.length || 0;
      setStatus("Content files are ready", `${rebuilt} page folder${rebuilt === 1 ? "" : "s"} refreshed.`);
    } catch (error) {
      setBusy(false);
      showDetails(error);
      setStatus("Could not refresh content files", error.error || "Something went wrong.", "error");
    }
  });
});

discoverButton.addEventListener("click", async () => {
  hideDetails();
  results.hidden = true;
  discoveryResults.hidden = true;
  activeJobId = null;
  activePages = [];
  activeAssets = [];
  setLinksFound(0);
  discIndicator.textContent = "";
  downloadButton.hidden = true;
  pauseButton.disabled = false;
  resumeButton.disabled = true;
  cancelButton.disabled = false;
  setCrawlControls(true);

  try {
    await getJson("/api/health");
    const start = await postJson("/api/jobs", {
      sourceUrl: startUrl.value,
      maxDepth: Number(maxDepth.value || 2),
      sameDomainOnly: sameDomain.checked,
      stayUnderStartPath: startPath.checked,
      includeImages: includeImages.checked,
      includeDocuments: includeDocuments.checked,
    });
    activeJobId = start.jobId;
    await postJson(`/api/jobs/${activeJobId}/discover`);
    const job = await pollJob(activeJobId, "Finding pages...", (latestJob) => {
      updateDiscoveryView(latestJob);
      discIndicator.textContent = latestJob.status === "paused" ? "Paused" : "Searching...";
    });
    updateDiscoveryView(job);
    setCrawlControls(false);
    discIndicator.textContent = "";
    setStatus("Choose what to save", `${job.pages?.length || 0} page link${job.pages?.length === 1 ? "" : "s"} added below. ${job.assets?.length || 0} file${job.assets?.length === 1 ? "" : "s"} found.`);
  } catch (error) {
    setBusy(false);
    setCrawlControls(false);
    discIndicator.textContent = "";
    showDetails(error);
    setStatus("Could not find pages", error.error || "Check the starting link and try again.", "error");
  }
});

downloadButton.addEventListener("click", async () => {
  if (!activeJobId) {
    setStatus("Find pages first", "Start with a page link, then choose what to save.", "error");
    return;
  }
  try {
    hideDetails();
    await syncPageSelectionFromTextbox();
    await postJson(`/api/jobs/${activeJobId}/download`);
    const job = await pollJob(activeJobId, "Downloading selected...");
    setCrawlControls(false);
    setStatus("Download finished", job.result?.output_root || "The files were saved.");
  } catch (error) {
    setBusy(false);
    setCrawlControls(false);
    showDetails(error);
    setStatus("Could not download selected", error.error || "Something went wrong.", "error");
  }
});

pauseButton.addEventListener("click", async () => {
  if (activeJobId) {
    pauseButton.disabled = true;
    resumeButton.disabled = false;
    showDetails(await postJson(`/api/jobs/${activeJobId}/pause`));
  }
});

resumeButton.addEventListener("click", async () => {
  if (activeJobId) {
    pauseButton.disabled = false;
    resumeButton.disabled = true;
    await postJson(`/api/jobs/${activeJobId}/resume`);
    showDetails(await getJson(`/api/jobs/${activeJobId}`));
  }
});

cancelButton.addEventListener("click", async () => {
  if (activeJobId) {
    await postJson(`/api/jobs/${activeJobId}/cancel`);
    setCrawlControls(false);
    showDetails(await getJson(`/api/jobs/${activeJobId}`));
  }
});

setLinksFound(0);
setCrawlControls(false);
downloadButton.hidden = true;
