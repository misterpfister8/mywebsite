(() => {
  const root = document.documentElement;
  const storageKey = 'misterpfister-theme';
  const themeColors = {
    dark: '#111310',
    light: '#f0f0e8',
  };

  // Keyed by the theme the button switches to: sun means "go light", moon means "go dark".
  const themeIcons = {
    light: '<circle cx="12" cy="12" r="4.1"/><path d="M12 2.5v2.4M12 19.1v2.4M4.9 4.9l1.7 1.7M17.4 17.4l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.9 19.1l1.7-1.7M17.4 6.6l1.7-1.7"/>',
    dark: '<path d="M20.1 13.6A8.1 8.1 0 1 1 10.4 3.9a6.5 6.5 0 0 0 9.7 9.7Z"/>',
  };

  let storedTheme = null;
  try {
    storedTheme = window.localStorage.getItem(storageKey);
  } catch {
    storedTheme = null;
  }

  let initialTheme;
  if (storedTheme === 'light' || storedTheme === 'dark') {
    initialTheme = storedTheme;
  } else {
    initialTheme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }
  root.dataset.theme = initialTheme;

  const initialThemeMeta = document.querySelector('meta[name="theme-color"]');
  if (initialThemeMeta) initialThemeMeta.content = themeColors[initialTheme];

  function syncThemeControls() {
    const currentTheme = root.dataset.theme === 'light' ? 'light' : 'dark';
    const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
    const nextLabel = nextTheme === 'light' ? 'Hell' : 'Dunkel';
    const accessibleLabel = nextTheme === 'light'
      ? 'Helles Farbschema verwenden'
      : 'Dunkles Farbschema verwenden';

    const themeMeta = document.querySelector('meta[name="theme-color"]');
    if (themeMeta) themeMeta.content = themeColors[currentTheme];

    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.setAttribute('aria-label', accessibleLabel);
      button.setAttribute('title', accessibleLabel);
      const label = button.querySelector('[data-theme-label]');
      if (label) label.textContent = nextLabel;
      const icon = button.querySelector('[data-theme-icon]');
      if (icon) icon.innerHTML = themeIcons[nextTheme];
    });
  }

  function toggleTheme() {
    const nextTheme = root.dataset.theme === 'light' ? 'dark' : 'light';
    root.classList.add('changing-theme');
    root.dataset.theme = nextTheme;
    // Commit the palette together so foreground/background never cross-fade apart.
    requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove('changing-theme')));

    try {
      window.localStorage.setItem(storageKey, nextTheme);
    } catch {
      // The selected theme still applies for this page view.
    }

    syncThemeControls();
  }

  function initializeThemeControls() {
    syncThemeControls();
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.addEventListener('click', toggleTheme);
    });
    root.classList.add('theme-enabled');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeThemeControls, { once: true });
  } else {
    initializeThemeControls();
  }
})();
