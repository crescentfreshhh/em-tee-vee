// Register the service worker so em tee vee is installable on Android tablets.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((e) => {
      console.warn("Service worker registration failed:", e);
    });
  });
}
