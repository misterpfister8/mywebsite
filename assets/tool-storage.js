/* Browser storage is optional. Never replace an unreadable backup implicitly. */
(() => {
  'use strict';
  globalThis.WorkshopStorage = function (key, preference, validate) {
    let unreadable = false;
    return {
      load() {
        let enabled = true;
        try {
          enabled = localStorage.getItem(preference) !== 'false';
          const raw = enabled ? localStorage.getItem(key) : null;
          if (raw && raw.length > 512 * 1024) throw new Error('size');
          return { enabled, data: raw ? validate(JSON.parse(raw)) : null, error: '' };
        } catch {
          unreadable = true;
          return { enabled, data: null, error: 'Sicherung nicht lesbar. Zum Zurücksetzen Speicherung aus- und einschalten.' };
        }
      },
      save(enabled, data) {
        try {
          if (!enabled) {
            // Remove personal data before writing the opt-out preference, even at quota.
            localStorage.removeItem(key);
            unreadable = false;
            localStorage.setItem(preference, 'false');
            return { text: 'Nur für diese Sitzung', error: false };
          }
          if (unreadable) return { text: 'Sicherung nicht lesbar. Speicherung aus- und einschalten zum Zurücksetzen.', error: true };
          localStorage.setItem(key, JSON.stringify(data));
          localStorage.setItem(preference, 'true');
          return { text: 'Lokal gespeichert', error: false };
        } catch {
          return { text: enabled ? 'Speichern nicht möglich. Sitzung bleibt nutzbar.' : 'Löschen nicht möglich. Browser-Speicherzugriff prüfen.', error: true };
        }
      },
    };
  };
})();
