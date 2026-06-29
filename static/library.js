(function () {
  const body = document.getElementById("lib-body");
  const emptyMsg = document.getElementById("lib-empty");
  const searchInput = document.getElementById("search");
  const filterBtns = document.querySelectorAll(".filter-btn");
  const profileSelect = document.getElementById("profile-select");
  const playerLink = document.getElementById("player-link");
  const modal = document.getElementById("match-modal");
  const matchUrl = document.getElementById("match-url");
  const matchSongInfo = document.getElementById("match-song-info");
  const matchError = document.getElementById("match-error");
  const matchSubmit = document.getElementById("match-submit");
  const matchCancel = document.getElementById("match-cancel");
  const modalClose = document.querySelector(".modal-close");
  const btnSync = document.getElementById("btn-sync");
  const syncStatus = document.getElementById("sync-status");
  const syncText = document.getElementById("sync-text");
  const syncFill = document.getElementById("sync-progress-fill");

  const params = new URLSearchParams(location.search);
  let activeProfile = params.get("profile") || "all";

  let library = [];
  let profileMap = {};
  let activeFilter = "all";
  let matchTarget = null;
  let syncPollTimer = null;

  async function loadProfiles() {
    const res = await fetch("/api/profiles");
    const profiles = await res.json();
    profileMap = {};
    profiles.forEach((p) => { profileMap[p.id] = p; });

    profileSelect.innerHTML = "";
    const everyone = new Option("Everyone", "all");
    profileSelect.appendChild(everyone);
    profiles.forEach((p) => {
      profileSelect.appendChild(new Option(p.name, p.id));
    });
    if (![...profileSelect.options].some((o) => o.value === activeProfile)) {
      activeProfile = "all";
    }
    profileSelect.value = activeProfile;
    updatePlayerLink();
  }

  function updatePlayerLink() {
    playerLink.href = `/player?profile=${encodeURIComponent(activeProfile)}`;
  }

  async function loadLibrary() {
    const res = await fetch(`/api/library?profile=${encodeURIComponent(activeProfile)}`);
    library = await res.json();
    render();
  }

  function likedByCell(song) {
    const ids = song.profiles || [];
    if (!ids.length) return "";
    return ids.map((id) => {
      const p = profileMap[id];
      if (!p) return "";
      return `<span class="liked-dot" title="${esc(p.name)}" style="background:${p.color}">${esc(p.name.slice(0,1).toUpperCase())}</span>`;
    }).join("");
  }

  function render() {
    const query = searchInput.value.toLowerCase();
    const filtered = library.filter((s) => {
      if (activeFilter === "downloaded" && s.status !== "downloaded") return false;
      if (activeFilter === "none" && s.status === "downloaded") return false;
      if (query) {
        const haystack = `${s.title} ${s.artist} ${s.album}`.toLowerCase();
        if (!haystack.includes(query)) return false;
      }
      return true;
    });

    body.innerHTML = "";

    if (library.length === 0) {
      emptyMsg.textContent = activeProfile === "all"
        ? "No songs yet. Add a profile and connect Spotify, then Sync."
        : "No songs for this profile yet. Hit Sync to pull their liked songs.";
      emptyMsg.classList.remove("hidden");
      return;
    }
    emptyMsg.classList.add("hidden");

    filtered.forEach((s) => {
      const tr = document.createElement("tr");
      const statusLabel = s.status === "downloaded" ? "Downloaded"
        : s.status === "missing" ? "File missing" : "No video";

      let videoCell = "-";
      if (s.status === "downloaded" && s.source_url) {
        videoCell = `<a href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.video_title || s.source_url)}</a>`;
      }
      const matchLabel = s.status === "downloaded" ? "Re-match" : "Match";

      tr.innerHTML = `
        <td class="col-status"><span class="status-dot ${esc(s.status)}" title="${statusLabel}"></span></td>
        <td class="col-title"><span class="td-title">${esc(s.title)}</span></td>
        <td class="col-artist"><span class="td-artist">${esc(s.artist)}</span></td>
        <td class="col-album"><span class="td-album">${esc(s.album || "")}</span></td>
        <td class="col-likedby">${likedByCell(s)}</td>
        <td class="col-video"><span class="td-video">${videoCell}</span></td>
        <td class="col-actions"><button class="btn-match" data-key="${esc(s.key)}">${matchLabel}</button></td>
      `;
      tr.querySelector(".btn-match").addEventListener("click", () => openModal(s));
      body.appendChild(tr);
    });
  }

  function openModal(song) {
    matchTarget = song;
    matchSongInfo.textContent = `${song.artist} — ${song.title}`;
    matchUrl.value = song.source_url || "";
    matchError.classList.add("hidden");
    matchSubmit.disabled = false;
    matchSubmit.textContent = "Download & Match";
    modal.classList.remove("hidden");
    matchUrl.focus();
  }
  function closeModal() {
    modal.classList.add("hidden");
    matchTarget = null;
    matchUrl.value = "";
  }

  matchCancel.addEventListener("click", closeModal);
  modalClose.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

  matchSubmit.addEventListener("click", async () => {
    const url = matchUrl.value.trim();
    if (!url) {
      matchError.textContent = "Please enter a URL.";
      matchError.classList.remove("hidden");
      return;
    }
    matchSubmit.disabled = true;
    matchSubmit.textContent = "Downloading...";
    matchError.classList.add("hidden");
    try {
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: matchTarget.key, url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Match failed");
      closeModal();
      loadLibrary();
    } catch (e) {
      matchError.textContent = e.message;
      matchError.classList.remove("hidden");
      matchSubmit.disabled = false;
      matchSubmit.textContent = "Download & Match";
    }
  });

  searchInput.addEventListener("input", render);

  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeFilter = btn.dataset.filter;
      render();
    });
  });

  profileSelect.addEventListener("change", () => {
    activeProfile = profileSelect.value;
    updatePlayerLink();
    const url = new URL(location);
    url.searchParams.set("profile", activeProfile);
    history.replaceState(null, "", url);
    loadLibrary();
  });

  btnSync.addEventListener("click", async () => {
    btnSync.disabled = true;
    syncStatus.classList.remove("hidden");
    syncText.textContent = "Starting sync...";
    syncFill.style.width = "0%";
    try {
      const res = await fetch("/api/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: activeProfile }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Sync failed");
      pollSync();
    } catch (e) {
      syncText.textContent = e.message;
      btnSync.disabled = false;
    }
  });

  function pollSync() {
    syncPollTimer = setInterval(async () => {
      const res = await fetch("/api/sync/status");
      const s = await res.json();
      if (s.total > 0) {
        const pct = Math.round((s.current / s.total) * 100);
        syncFill.style.width = pct + "%";
        const who = s.profile ? `${s.profile}: ` : "";
        syncText.textContent = s.current_song
          ? `${who}Downloading ${s.current}/${s.total}: ${s.current_song}`
          : `${who}${s.current}/${s.total} complete`;
      } else if (s.running) {
        syncText.textContent = s.profile ? `Fetching ${s.profile}'s liked songs...` : "Fetching liked songs...";
      }
      if (!s.running) {
        clearInterval(syncPollTimer);
        btnSync.disabled = false;
        if (s.errors.length > 0) {
          syncText.textContent = `Done with ${s.errors.length} error(s)`;
        } else {
          syncText.textContent = "Sync complete!";
          setTimeout(() => syncStatus.classList.add("hidden"), 3000);
        }
        loadProfiles();
        loadLibrary();
      }
    }, 2000);
  }

  document.addEventListener("keydown", (e) => { if (e.code === "Escape") closeModal(); });

  function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  (async function init() {
    await loadProfiles();
    await loadLibrary();
  })();
})();
