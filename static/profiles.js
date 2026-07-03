(function () {
  const grid = document.getElementById("profiles-grid");
  const emptyMsg = document.getElementById("profile-empty");
  const addModal = document.getElementById("add-modal");
  const nameInput = document.getElementById("profile-name");
  const addError = document.getElementById("add-error");
  const addSubmit = document.getElementById("add-submit");

  let profiles = [];

  async function load() {
    const res = await fetch("/api/profiles");
    profiles = await res.json();
    render();
  }

  function initials(name) {
    return name.trim().slice(0, 2).toUpperCase();
  }

  function render() {
    grid.innerHTML = "";

    // "Everyone" tile (plays the whole family's combined library)
    if (profiles.length > 0) {
      grid.appendChild(card({
        avatarClass: "everyone",
        avatarText: "&#9835;",
        name: "Everyone",
        meta: "Whole family mix",
        onClick: () => goPlay("all"),
      }));
    }

    profiles.forEach((p) => {
      const meta = p.authed
        ? `${p.video_count}/${p.song_count} videos`
        : `<span class="badge-unlinked">Connect Spotify</span>`;

      const c = card({
        avatarStyle: `background:${p.color}`,
        avatarText: esc(initials(p.name)),
        name: esc(p.name),
        meta: meta,
        onClick: () => {
          if (p.authed) goPlay(p.id);
          else connectSpotify(p.id);
        },
      });

      const actions = document.createElement("div");
      actions.className = "card-actions";

      const syncBtn = document.createElement("button");
      syncBtn.innerHTML = "&#8635;";
      syncBtn.title = p.authed ? "Sync liked songs" : "Connect Spotify";
      syncBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (p.authed) syncProfile(p.id);
        else connectSpotify(p.id);
      });

      const delBtn = document.createElement("button");
      delBtn.innerHTML = "&times;";
      delBtn.title = "Remove profile";
      delBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        removeProfile(p);
      });

      actions.appendChild(syncBtn);
      actions.appendChild(delBtn);
      c.appendChild(actions);
      grid.appendChild(c);
    });

    // Add-profile tile
    grid.appendChild(card({
      cardClass: "add-card",
      avatarText: "+",
      name: "Add Profile",
      meta: "",
      onClick: openAdd,
    }));

    emptyMsg.classList.toggle("hidden", profiles.length > 0);
  }

  function card({ cardClass = "", avatarClass = "", avatarStyle = "", avatarText, name, meta, onClick }) {
    const el = document.createElement("div");
    el.className = `profile-card ${cardClass}`;
    el.innerHTML = `
      <div class="avatar ${avatarClass}" style="${avatarStyle}">${avatarText}</div>
      <div class="profile-name">${name}</div>
      <div class="profile-meta">${meta || ""}</div>
    `;
    el.querySelector(".avatar").addEventListener("click", onClick);
    el.querySelector(".profile-name").addEventListener("click", onClick);
    return el;
  }

  function goPlay(profileId) {
    location.href = `/player?profile=${encodeURIComponent(profileId)}`;
  }

  function connectSpotify(profileId) {
    location.href = `/auth/login/${encodeURIComponent(profileId)}`;
  }

  async function syncProfile(profileId) {
    await fetch("/api/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_id: profileId }),
    });
    location.href = `/library?profile=${encodeURIComponent(profileId)}`;
  }

  async function removeProfile(p) {
    if (!confirm(`Remove ${p.name}? Their Spotify connection and song tags are deleted. Shared videos stay.`)) return;
    await fetch(`/api/profiles/${p.id}`, { method: "DELETE" });
    load();
  }

  // ----- add modal
  function openAdd() {
    addError.classList.add("hidden");
    nameInput.value = "";
    addModal.classList.remove("hidden");
    nameInput.focus();
  }
  function closeAdd() { addModal.classList.add("hidden"); }

  document.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", closeAdd));
  addModal.addEventListener("click", (e) => { if (e.target === addModal) closeAdd(); });

  addSubmit.addEventListener("click", async () => {
    const name = nameInput.value.trim();
    if (!name) {
      addError.textContent = "Please enter a name.";
      addError.classList.remove("hidden");
      return;
    }
    addSubmit.disabled = true;
    try {
      const res = await fetch("/api/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Could not create profile");
      closeAdd();
      // Send them straight to Spotify to connect the new profile.
      connectSpotify(data.id);
    } catch (e) {
      addError.textContent = e.message;
      addError.classList.remove("hidden");
      addSubmit.disabled = false;
    }
  });

  nameInput && nameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") addSubmit.click();
  });

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  load();
})();
