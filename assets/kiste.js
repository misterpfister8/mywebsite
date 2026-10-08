/* Pfisterkiste page: a playable 3 × 3 slide puzzle. Starts like the app icon, one move from solved.
   Tiles are buttons; arrow keys slide the neighbour of the gap. Each tile has one position value (--x, --y). */
(() => {
  'use strict';
  const root = document.querySelector('[data-kiste-puzzle]');
  if (!root) return;
  const n = 3, solved = [1, 2, 3, 4, 5, 6, 7, 8, 0];
  const status = root.querySelector('[data-kiste-status]'), shuffleButton = root.querySelector('[data-kiste-shuffle]');
  const tiles = new Map([...root.querySelectorAll('[data-tile]')].map((el) => [Number(el.dataset.tile), el]));
  let board = [1, 2, 3, 4, 5, 6, 7, 0, 8], moves = 0;

  const isSolved = () => board.every((v, i) => v === solved[i]);
  const say = (html) => { status.innerHTML = html; };

  function render() {
    const gap = board.indexOf(0), done = isSolved();
    board.forEach((v, i) => {
      if (!v) return;
      const el = tiles.get(v), x = i % n, y = Math.floor(i / n);
      el.style.setProperty('--x', x); el.style.setProperty('--y', y);
      el.disabled = done || (x !== gap % n && y !== Math.floor(gap / n));
      el.setAttribute('aria-label', `${v}, Reihe ${y + 1}, Spalte ${x + 1}`);
    });
  }

  // Slides the tile at index i and every tile between it and the gap (same row or column).
  function slide(i) {
    let gap = board.indexOf(0);
    const sameRow = Math.floor(i / n) === Math.floor(gap / n), sameCol = i % n === gap % n;
    if (i === gap || !(sameRow || sameCol)) return false;
    const step = (sameRow ? 1 : n) * Math.sign(i - gap);
    while (gap !== i) { board[gap] = board[gap + step]; board[gap + step] = 0; gap += step; moves++; }
    return true;
  }

  function play(i) {
    if (isSolved() || !slide(i)) return;
    const focused = root.querySelector('.kiste-board').contains(document.activeElement);
    render();
    if (isSolved()) {
      root.dataset.solved = '';
      if (focused) shuffleButton.focus(); // the solved tiles are disabled now
      say(`<strong>Gelöst!</strong> In ${moves} ${moves === 1 ? 'Zug' : 'Zügen'}. In der App gibt es dazu Bestwerte und eine Fanfare.`);
      shuffleButton.textContent = 'Nochmal mischen';
    } else {
      say(`${moves} ${moves === 1 ? 'Zug' : 'Züge'}`);
    }
  }

  // Random walk of the gap: always solvable, never already solved.
  function shuffle() {
    do {
      let previous = -1;
      for (let k = 0; k < 80; k++) {
        const gap = board.indexOf(0), x = gap % n, y = Math.floor(gap / n);
        const options = [x > 0 && gap - 1, x < n - 1 && gap + 1, y > 0 && gap - n, y < n - 1 && gap + n].filter((v) => v !== false && v !== previous);
        const pick = options[Math.floor(Math.random() * options.length)];
        board[gap] = board[pick]; board[pick] = 0; previous = gap;
      }
    } while (isSolved());
    moves = 0;
    delete root.dataset.solved;
    shuffleButton.textContent = 'Mischen';
    render();
    say('Gemischt. Bring die Zahlen in die Reihenfolge 1 bis 8.');
  }

  root.addEventListener('click', (e) => {
    const el = e.target.closest('[data-tile]');
    if (el && !el.disabled) play(board.indexOf(Number(el.dataset.tile)));
  });
  // Arrow keys move the tile that sits on the opposite side of the gap.
  root.addEventListener('keydown', (e) => {
    const dir = { ArrowLeft: [1, 0], ArrowRight: [-1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] }[e.key];
    if (!dir || !e.target.closest('.kiste-board')) return;
    const gap = board.indexOf(0), x = gap % n + dir[0], y = Math.floor(gap / n) + dir[1];
    if (x < 0 || y < 0 || x >= n || y >= n) return;
    e.preventDefault();
    const value = board[y * n + x];
    play(y * n + x);
    if (!tiles.get(value).disabled) tiles.get(value).focus();
  });
  shuffleButton.addEventListener('click', shuffle);
  render();
})();
