const statusEl = document.getElementById("status");

document.getElementById("startRun").addEventListener("click", () => {
  chrome.runtime.sendMessage(
    { type: "START_RUN" },
    (response) => {
      if (chrome.runtime.lastError) {
        statusEl.textContent = "Error starting run.";
        console.error(chrome.runtime.lastError);
        return;
      }
      statusEl.textContent = `Run started: ${response && response.run_id}`;
    }
  );
});

document.getElementById("endRun").addEventListener("click", () => {
  // v1: send minimal metadata; you can expand later
  chrome.runtime.sendMessage(
    {
      type: "END_RUN",
      runMeta: {
        result: "Unknown",           // you can manually edit later or improve logic
        final_stage: null,
        final_boss: null,
        starter_species: null,
        run_tag: null
      }
    },
    (response) => {
      if (chrome.runtime.lastError) {
        statusEl.textContent = "Error ending run.";
        console.error(chrome.runtime.lastError);
        return;
      }
      statusEl.textContent = "Run ended and saved as JSON.";
    }
  );
});
