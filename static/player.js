(function () {
  const player = document.getElementById("player");
  const titleEl = document.getElementById("song-title");
  const artistEl = document.getElementById("song-artist");
  const playlistEl = document.getElementById("playlist");
  const btnPlay = document.getElementById("btn-play");
  const btnNext = document.getElementById("btn-next");
  const btnPrev = document.getElementById("btn-prev");
  const btnShuffle = document.getElementById("btn-shuffle");
  const btnSync = document.getElementById("btn-sync");
  const syncStatus = document.getElementById("sync-status");
  const syncText = document.getElementById("sync-text");
  const syncFill = document.getElementById("sync-progress-fill");

  let queue = [];
  let currentIndex = -1;
  let syncPollTimer = null;

  function shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  async function loadVideos() {
    const res = await fetch("/api/videos");
    const videos = await res.json();
    queue = shuffle(videos);
    renderPlaylist();
    if (queue.length > 0 && currentIndex === -1) {
      playIndex(0);
    }
  }

  function renderPlaylist() {
    playlistEl.innerHTML = "";
    queue.forEach((v, i) => {
      const li = document.createElement("li");
      li.innerHTML = `<div class="pl-title">${esc(v.title)}</div><div class="pl-artist">${esc(v.artist)}</div>`;
      if (i === currentIndex) li.classList.add("active");
      li.addEventListener("click", () => playIndex(i));
      playlistEl.appendChild(li);
    });
  }

  function playIndex(i) {
    if (i < 0 || i >= queue.length) return;
    currentIndex = i;
    const v = queue[i];
    player.src = `/videos/${v.file}`;
    player.play();
    titleEl.textContent = v.title;
    artistEl.textContent = v.artist;
    btnPlay.innerHTML = "&#10074;&#10074;";
    renderPlaylist();

    const activeLi = playlistEl.querySelector("li.active");
    if (activeLi) activeLi.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  player.addEventListener("ended", () => {
    if (currentIndex < queue.length - 1) {
      playIndex(currentIndex + 1);
    } else {
      queue = shuffle(queue);
      playIndex(0);
    }
  });

  btnPlay.addEventListener("click", () => {
    if (player.paused) {
      player.play();
      btnPlay.innerHTML = "&#10074;&#10074;";
    } else {
      player.pause();
      btnPlay.innerHTML = "&#9654;";
    }
  });

  btnNext.addEventListener("click", () => {
    if (currentIndex < queue.length - 1) playIndex(currentIndex + 1);
    else { queue = shuffle(queue); playIndex(0); }
  });

  btnPrev.addEventListener("click", () => {
    if (player.currentTime > 5) {
      player.currentTime = 0;
    } else if (currentIndex > 0) {
      playIndex(currentIndex - 1);
    }
  });

  btnShuffle.addEventListener("click", () => {
    const current = queue[currentIndex];
    queue = shuffle(queue);
    currentIndex = current ? queue.indexOf(current) : 0;
    renderPlaylist();
  });

  btnSync.addEventListener("click", async () => {
    btnSync.disabled = true;
    syncStatus.classList.remove("hidden");
    syncText.textContent = "Starting sync...";
    syncFill.style.width = "0%";

    try {
      await fetch("/api/sync", { method: "POST" });
      pollSync();
    } catch (e) {
      syncText.textContent = "Sync failed: " + e.message;
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
        syncText.textContent = s.current_song
          ? `Downloading ${s.current}/${s.total}: ${s.current_song}`
          : `${s.current}/${s.total} complete`;
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
        loadVideos();
      }
    }, 2000);
  }

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  document.addEventListener("keydown", (e) => {
    if (e.code === "Space") { e.preventDefault(); btnPlay.click(); }
    if (e.code === "ArrowRight") btnNext.click();
    if (e.code === "ArrowLeft") btnPrev.click();
  });

  loadVideos();
})();
