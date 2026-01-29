const browserApi = typeof browser !== "undefined" ? browser : chrome;
let slotId = -1;

// --- Pokerogue Tableau tracking state ---
let currentRun = null;
let encounterBuffer = [];
let battleIndex = 0;

// Track last waveIndex we logged so we don't duplicate encounters
let lastLoggedWaveIndex = null;

function startRun() {
  const now = new Date().toISOString();
  currentRun = {
    run_id: `run_${now}`,
    start_timestamp: now,
    end_timestamp: null,
    result: null,
    final_stage: null,
    final_boss: null,
    starter_species: null,
    total_battles: null,
    run_tag: null
  };
  encounterBuffer = [];
  battleIndex = 0;
  lastLoggedWaveIndex = null;
  console.log("Pokerogue tracker: started run", currentRun.run_id);
}

function endRun(runMeta) {
  if (!currentRun) {
    console.warn("Pokerogue tracker: endRun called but no active run");
    return;
  }
  const now = new Date().toISOString();
  currentRun.end_timestamp = now;

  // Allow metadata (result, final_stage, starter_species, run_tag, etc.)
  if (runMeta && typeof runMeta === "object") {
    Object.assign(currentRun, runMeta);
  }

  currentRun.total_battles = encounterBuffer.length;

  const payload = {
    run: currentRun,
    encounters: encounterBuffer
  };

  // Convert payload to JSON string
  const json = JSON.stringify(payload, null, 2);

  // Build a data URL (no Blob, no createObjectURL)
  const dataUrl =
    "data:application/json;charset=utf-8," + encodeURIComponent(json);

  const safeRunId = currentRun.run_id.replace(/[:]/g, "-");

  browserApi.downloads.download(
    {
      url: dataUrl,
      filename: `pokerogue_runs/${safeRunId}.json`,
      saveAs: false
    },
    (downloadId) => {
      console.log("Pokerogue tracker: download started", downloadId);
    }
  );

  console.log(
    "Pokerogue tracker: ended run",
    currentRun.run_id,
    "with",
    encounterBuffer.length,
    "encounters"
  );

  currentRun = null;
  encounterBuffer = [];
  battleIndex = 0;
  lastLoggedWaveIndex = null;
}

function updateDiv(pokemon, weather, message) {
  browserApi.tabs.query({ active: true, currentWindow: true }, function (tabs) {
    browserApi.tabs.sendMessage(
      tabs[0].id,
      { type: message, pokemon: pokemon, weather: weather, slotId: slotId },
      (response) => {
        if (response && response.success) {
          console.log("Div updated successfully");
        } else {
          console.error("Failed to update div");
        }
      }
    );
  });
}

function sortById(a, b) {
  if (a.id > b.id) return 1;
  else if (a.id < b.id) return -1;
  else return 0;
}

// message can be either "UPDATE_ALLIES_DIV" or "UPDATE_ENEMIES_DIV"
function appendPokemonArrayToDiv(pokemonArray, arena, message) {
  let frontendPokemonArray = [];
  let itemsProcessed = 0;
  pokemonArray.forEach((pokemon, index, array) => {
    const pokemonId = Utils.convertPokemonId(pokemon.species);
    let weather = {};
    if (arena.weather && arena.weather.weatherType) {
      weather = {
        type: WeatherType[arena.weather.weatherType],
        turnsLeft: arena.weather.turnsLeft || 0
      };
    }
    PokeApi.getAbility(pokemonId, pokemon.abilityIndex).then((ability) => {
      Utils.getPokemonTypeEffectiveness(pokemonId).then((typeEffectiveness) => {
        console.log(
          "Got pokemon",
          pokemonId,
          "ability",
          ability,
          "type effectiveness",
          typeEffectiveness
        );
        frontendPokemonArray.push({
          id: pokemonId,
          typeEffectiveness: {
            weaknesses: Array.from(typeEffectiveness.weaknesses),
            resistances: Array.from(typeEffectiveness.resistances),
            immunities: Array.from(typeEffectiveness.immunities)
          },
          ivs: pokemon.ivs,
          ability: ability,
          nature: {
            name: Nature[pokemon.nature],
            description: PokeRogueUtils.getNatureDescription(pokemon.nature)
          }
        });
        itemsProcessed++;
        if (itemsProcessed === array.length) {
          updateDiv(frontendPokemonArray.sort(sortById), weather, message);
        }
      });
    });
  });
}

// --- NEW: shared helper to log encounters from any session-like object ---
function logEncounterFromSession(sessionData) {
  if (!currentRun) return;
  if (!sessionData) return;
  if (
    !Array.isArray(sessionData.enemyParty) ||
    sessionData.enemyParty.length === 0
  )
    return;

  const waveIndex =
    typeof sessionData.waveIndex === "number" ? sessionData.waveIndex : null;

  // If Pokerogue spams multiple updates for the same wave, only log once
  if (waveIndex !== null && waveIndex === lastLoggedWaveIndex) {
    return;
  }

  const firstEnemy = sessionData.enemyParty[0];
  const pokemonId = Utils.convertPokemonId(firstEnemy.species);
  const encounterId = `${currentRun.run_id}_${battleIndex
    .toString()
    .padStart(3, "0")}`;

  console.log(
    "Pokerogue tracker: logging encounter",
    encounterId,
    "waveIndex:",
    waveIndex,
    "enemy_species:",
    pokemonId,
    "enemy_level:",
    firstEnemy.level
  );

  encounterBuffer.push({
    encounter_id: encounterId,
    battle_index: battleIndex,
    enemy_species: pokemonId, // numeric ID for now
    enemy_type1: null,
    enemy_type2: null,
    enemy_level: firstEnemy.level || null,
    is_boss: false,
    encounter_result: null,
    enemy_ended_run: false,
    notes: null
  });

  battleIndex++;
  if (waveIndex !== null) {
    lastLoggedWaveIndex = waveIndex;
  }
}

// --- Message handling from content / popup ---
browserApi.runtime.onMessage.addListener(function (
  request,
  sender,
  sendResponse
) {
  // Happens when loading a savegame or continuing an old run
  if (request.type === "BG_GET_SAVEDATA") {
    const savedata = request.data;
    slotId = request.slotId;
    console.log("Received save data", savedata);

    appendPokemonArrayToDiv(
      Utils.mapPartyToPokemonArray(savedata.enemyParty),
      savedata.arena,
      "UPDATE_ENEMIES_DIV"
    );
    appendPokemonArrayToDiv(
      Utils.mapPartyToPokemonArray(savedata.party),
      savedata.arena,
      "UPDATE_ALLIES_DIV"
    );

    // Also log an encounter from this session snapshot
    logEncounterFromSession(savedata);

    sendResponse && sendResponse({ success: true });
    return;
  }

  // From popup: start a new run manually
  if (request.type === "START_RUN") {
    startRun();
    sendResponse &&
      sendResponse({
        success: true,
        run_id: currentRun && currentRun.run_id
      });
    return;
  }

  // From popup: end the current run manually (with optional metadata)
  if (request.type === "END_RUN") {
    endRun(request.runMeta || {});
    sendResponse && sendResponse({ success: true });
    return;
  }
});

// --- Network interception for live session updates ---
browserApi.webRequest.onBeforeRequest.addListener(
  function (details) {
    if (details.method !== "POST") {
      return;
    }

    try {
      let sessionData = JSON.parse(
        new TextDecoder().decode(details.requestBody.raw[0].bytes)
      );
      console.log("POST Session data:", sessionData);

      if (details.url.includes("updateall")) {
        sessionData = sessionData.session;
      }

      // Existing overlay updates
      appendPokemonArrayToDiv(
        Utils.mapPartyToPokemonArray(sessionData.enemyParty),
        sessionData.arena,
        "UPDATE_ENEMIES_DIV"
      );
      appendPokemonArrayToDiv(
        Utils.mapPartyToPokemonArray(sessionData.party),
        sessionData.arena,
        "UPDATE_ALLIES_DIV"
      );

      // Log encounter using the shared helper
      logEncounterFromSession(sessionData);
    } catch (e) {
      console.error("Error while intercepting web request: ", e);
    }
  },
  {
    urls: [
      "https://api.pokerogue.net/savedata/update?datatype=1*",
      "https://api.pokerogue.net/savedata/updateall"
    ]
  },
  ["requestBody"]
);
