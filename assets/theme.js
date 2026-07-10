(() => {
  const root = document.documentElement;
  const storageKey = 'misterpfister-theme';
  const themeColors = {
    dark: '#0f1110',
    light: '#f3eee3',
  };

  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  if (isIOS) {
    const viewportMeta = document.querySelector('meta[name="viewport"]');
    if (viewportMeta && !viewportMeta.content.includes('maximum-scale')) {
      viewportMeta.content += ', maximum-scale=1';
    }
  }

  let storedTheme = null;
  try {
    storedTheme = window.localStorage.getItem(storageKey);
  } catch {
    storedTheme = null;
  }

  const initialTheme = storedTheme === 'light' ? 'light' : 'dark';
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
    });
  }

  function toggleTheme() {
    const nextTheme = root.dataset.theme === 'light' ? 'dark' : 'light';
    root.dataset.theme = nextTheme;

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
