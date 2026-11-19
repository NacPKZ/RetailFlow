// characters.js — personnages en pixel art, dessinés en code (aucun fichier image).
// Chaque sprite est une petite grille de caractères : une lettre = une couleur.
window.RF = window.RF || {};

RF.characters = (() => {
  // 7 colonnes x 9 lignes, vue de dessus légèrement inclinée.
  const BODY = [
    "..hhh..",
    ".hhhhh.",
    ".hsssh.",
    "..sss..",
    ".ccccc.",
    "scccccs",
    ".ccccc.",
    ".pp.pp.",
    ".ff.ff.",
  ];
  const STEP = [".pp..p.", ".ff..f."]; // jambes en mouvement (2e image de marche)
  const VARIANTS = [
    { h: "#4a3222", s: "#f1c7a0", c: "#3f7fbf", p: "#2f3b52", f: "#1d1d1d" },
    { h: "#d9a441", s: "#e8b48a", c: "#d0584a", p: "#4b4b4b", f: "#1d1d1d" },
    { h: "#1f1f1f", s: "#9a6a47", c: "#5aa469", p: "#38425a", f: "#1d1d1d" },
  ];
  const CASHIER = { h: "#2b2b2b", s: "#f1c7a0", c: "#f2b84b", p: "#2f3b52", f: "#1d1d1d" };
  const BADGES = {
    en_transfert: { color: "#f2b84b", symbol: "⇄" },
    abandon: { color: "#c4473a", symbol: "✕" },
    en_service: { color: "#3fae5a", symbol: "€" },
  };

  function drawSprite(ctx, rows, palette, centerX, bottomY, pixel) {
    const left = Math.round(centerX - (rows[0].length * pixel) / 2);
    const top = Math.round(bottomY - rows.length * pixel);
    rows.forEach((row, y) => {
      [...row].forEach((code, x) => {
        if (code === ".") return;
        ctx.fillStyle = palette[code];
        ctx.fillRect(Math.round(left + x * pixel), Math.round(top + y * pixel),
          Math.ceil(pixel), Math.ceil(pixel));
      });
    });
    return top;
  }

  /** Dessine un client ; en mouvement, il alterne deux poses de jambes (marche). */
  function drawCustomer(ctx, customer, x, y, unit, frame, followed) {
    const pixel = spritePixel(unit);
    const rows = customer.moving && Math.floor(frame / 6) % 2 === 1
      ? [...BODY.slice(0, 7), ...STEP] : BODY;
    const palette = customer.state === "abandon" ? faded(VARIANTS[customer.id % 3])
      : VARIANTS[customer.id % VARIANTS.length];
    const top = drawSprite(ctx, rows, palette, x, y + pixel * 4, pixel);
    if (followed) {
      ctx.strokeStyle = "#9467bd";
      ctx.lineWidth = 3;
      ctx.strokeRect(x - pixel * 5, top - pixel * 2, pixel * 10, pixel * 14);
    }
    const badge = BADGES[customer.state];
    if (badge) drawBadge(ctx, badge, x + pixel * 4, top, pixel);
  }

  function drawCashier(ctx, x, y, unit, isPresent, scanning) {
    if (!isPresent) return;
    const pixel = spritePixel(unit);
    drawSprite(ctx, BODY, CASHIER, x, y + pixel * 4, pixel);
    if (scanning) { // éclair rouge du lecteur de code-barres
      ctx.fillStyle = "#ff3b3b";
      ctx.fillRect(x + unit * 0.45, y - unit * 0.1, unit * 0.5, Math.max(2, pixel));
    }
  }

  function drawBadge(ctx, badge, x, y, pixel) {
    const size = pixel * 5;
    ctx.fillStyle = badge.color;
    ctx.fillRect(x - size / 2, y - size, size, size);
    ctx.fillStyle = "#ffffff";
    ctx.font = `bold ${size - 2}px monospace`;
    ctx.textAlign = "center";
    ctx.fillText(badge.symbol, x, y - pixel);
  }

  /** Taille d'un « pixel » de sprite : un personnage fait ~0,8 case de haut. */
  function spritePixel(unit) {
    return Math.max(1, unit / 11);
  }

  function faded(palette) {
    return { ...palette, c: "#9a9a9a", p: "#6d6d6d" };
  }

  return { drawCustomer, drawCashier };
})();
