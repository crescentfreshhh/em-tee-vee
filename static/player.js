(function () {
  const player = document.getElementById("player");
  const titleEl = document.getElementById("song-title");
  const artistEl = document.getElementById("song-artist");
  const playlistEl = document.getElementById("playlist");
  const btnPlay = document.getElementById("btn-play");
  const btnNext = document.getElementById("btn-next");
  const btnPrev = document.getElementById("btn-prev");
  const btnShuffle = document.getElementById("btn-shuffle");
  const btnFullscreen = document.getElementById("btn-fullscreen");
  const profileLabel = document.getElementById("profile-label");
  const libraryLink = document.getElementById("library-link");
  const playerContainer = document.getElementById("player-container");

  const params = new URLSearchParams(location.search);
  const profile = params.get("profile") || "all";

  // Carry the selected profile through to the library page.
  libraryLink.href = `/library?profile=${encodeURIComponent(profile)}`;

  let queue = [];
  let currentIndex = -1;

  function shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  async function loadProfileLabel() {
    if (profile === "all") { profileLabel.textContent = "Everyone"; return; }
    try {
      const res = await fetch("/api/profiles");
      const profiles = await res.json();
      const p = profiles.find((x) => x.id === profile);
      if (p) {
        profileLabel.textContent = p.name;
        profileLabel.style.color = p.color;
      }
    } catch (e) { /* non-fatal */ }
  }

  async function loadVideos() {
    const res = await fetch(`/api/videos?profile=${encodeURIComponent(profile)}`);
    const videos = await res.json();
    queue = shuffle(videos);
    renderPlaylist();
    if (queue.length > 0 && currentIndex === -1) playIndex(0);
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

  function advance() {
    if (currentIndex < queue.length - 1) playIndex(currentIndex + 1);
    else { queue = shuffle(queue); playIndex(0); }
  }

  player.addEventListener("ended", advance);

  btnPlay.addEventListener("click", () => {
    if (player.paused) { player.play(); btnPlay.innerHTML = "&#10074;&#10074;"; }
    else { player.pause(); btnPlay.innerHTML = "&#9654;"; }
  });

  btnNext.addEventListener("click", advance);

  btnPrev.addEventListener("click", () => {
    if (player.currentTime > 5) player.currentTime = 0;
    else if (currentIndex > 0) playIndex(currentIndex - 1);
  });

  btnShuffle.addEventListener("click", () => {
    const current = queue[currentIndex];
    queue = shuffle(queue);
    currentIndex = current ? queue.indexOf(current) : 0;
    renderPlaylist();
  });

  btnFullscreen.addEventListener("click", () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else playerContainer.requestFullscreen && playerContainer.requestFullscreen();
  });

  document.addEventListener("keydown", (e) => {
    if (e.code === "Space") { e.preventDefault(); btnPlay.click(); }
    if (e.code === "ArrowRight") btnNext.click();
    if (e.code === "ArrowLeft") btnPrev.click();
    if (e.key === "f") btnFullscreen.click();
  });

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  loadProfileLabel();
  loadVideos();
})();
