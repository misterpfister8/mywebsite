(() => {
  const panel = document.querySelector(".sculpture-panel");
  if (!panel) return;
  const button = panel.querySelector(".motion-toggle");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  let paused = reduced.matches;
  function sync() {
    panel.classList.toggle("paused", paused || reduced.matches);
    button.textContent = paused ? "Bewegung starten" : "Bewegung pausieren";
    button.setAttribute("aria-pressed", String(paused));
    button.hidden = reduced.matches;
  }
  button.addEventListener("click", () => {
    paused = !paused;
    sync();
  });
  reduced.addEventListener("change", () => {
    paused = reduced.matches;
    sync();
  });
  panel.addEventListener("pointermove", (event) => {
    if (paused || reduced.matches || event.pointerType === "touch") return;
    const rect = panel.getBoundingClientRect();
    panel.style.setProperty(
      "--pointer-x",
      `${((event.clientX - rect.left) / rect.width - 0.5) * 16}deg`,
    );
    panel.style.setProperty(
      "--pointer-y",
      `${((event.clientY - rect.top) / rect.height - 0.5) * -12}deg`,
    );
  });
  panel.addEventListener("pointerleave", () => {
    panel.style.setProperty("--pointer-x", "0deg");
    panel.style.setProperty("--pointer-y", "0deg");
  });
  new IntersectionObserver(([entry]) =>
    panel.classList.toggle("offscreen", !entry.isIntersecting),
  ).observe(panel);
  document.addEventListener("visibilitychange", () =>
    panel.classList.toggle("offscreen", document.hidden),
  );
  sync();
})();
