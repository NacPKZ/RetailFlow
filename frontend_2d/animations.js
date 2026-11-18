// animations.js — échantillonnage des trajectoires calculées en Python.
// Même règle que queuesmart/scene/tracks.py : interpolation linéaire entre deux
// images clés, l'état d'un segment est celui de son image clé de départ.
// Aucune décision métier ici : on lit seulement [temps, x, y, état].
window.RF = window.RF || {};

RF.anim = (() => {
  const GONE = "parti";

  /** Indice de la dernière image clé atteinte à l'instant t (recherche dichotomique). */
  function segmentIndex(keyframes, t) {
    let low = 0;
    let high = keyframes.length - 1;
    if (t < keyframes[0][0]) return -1;
    while (low < high) {
      const middle = Math.ceil((low + high) / 2);
      if (keyframes[middle][0] <= t) low = middle; else high = middle - 1;
    }
    return low;
  }

  /** Position et état d'un client à l'instant t, ou null s'il n'est pas visible. */
  function sample(keyframes, t) {
    const index = segmentIndex(keyframes, t);
    if (index < 0) return null;
    const [t0, x0, y0, state] = keyframes[index];
    if (state === GONE) return null;
    const next = keyframes[index + 1];
    if (!next) return { x: x0, y: y0, state, moving: false };
    const progress = Math.min(1, Math.max(0, (t - t0) / (next[0] - t0)));
    const moving = next[1] !== x0 || next[2] !== y0;
    return { x: x0 + (next[1] - x0) * progress, y: y0 + (next[2] - y0) * progress, state, moving };
  }

  /** Dernier état connu d'une caisse : [temps, ouverte, client servi]. */
  function registerAt(states, t) {
    return states[Math.max(0, segmentIndex(states, t))];
  }

  return { sample, registerAt };
})();
