// map.js — décor du magasin : sol, murs, portes, rayons, caisses et caissiers.
// Les coordonnées viennent de SceneLayout (Python) : ce fichier ne fait que dessiner.
window.RF = window.RF || {};

RF.map = (() => {
  const COLORS = {
    floorA: "#edf0ed", floorB: "#e5e9e5", wall: "#263e54", aisle: "#dae3df",
    shelf: "#718c8d", belt: "#2d2d33", beltLine: "#55555f", desk: "#c9ccd3",
    open: "#258778", closed: "#bb5b67", sign: "#14233b", signText: "#ffffff",
    door: "#7fb3d5", text: "#14233b",
  };
  const PRODUCTS = ["#e05d5d", "#f2b84b", "#5aa469", "#4f86c6", "#b07cc6", "#f08a4b"];

  function draw(ctx, layout, unit, registerStates, frame) {
    drawFloor(ctx, layout, unit);
    drawShelves(ctx, layout, unit);
    drawDoors(ctx, layout, unit);
    layout.registers.forEach((register) => {
      drawRegister(ctx, layout, unit, register, registerStates[register.id], frame);
    });
  }

  function drawFloor(ctx, layout, unit) {
    for (let x = 0; x < layout.width; x += 1) {
      for (let y = 0; y < layout.height; y += 1) {
        ctx.fillStyle = (x + y) % 2 === 0 ? COLORS.floorA : COLORS.floorB;
        ctx.fillRect(x * unit, y * unit, unit + 1, unit + 1);
      }
    }
    ctx.fillStyle = COLORS.aisle;
    ctx.fillRect(0, (layout.main_aisle_y - 0.6) * unit, layout.width * unit, 1.2 * unit);
    ctx.fillStyle = COLORS.wall;
    ctx.fillRect(0, 0, layout.width * unit, 0.25 * unit);
  }

  function drawShelves(ctx, layout, unit) {
    const top = layout.main_aisle_y + 1.2;
    for (let x = 1.5; x + 2.6 < layout.width - 0.5; x += 3.5) {
      ctx.fillStyle = COLORS.shelf;
      ctx.fillRect(x * unit, top * unit, 2.6 * unit, (layout.height - top - 0.6) * unit);
      for (let row = 0; row < 4; row += 1) {
        for (let item = 0; item < 5; item += 1) {
          ctx.fillStyle = PRODUCTS[(row * 5 + item + Math.floor(x)) % PRODUCTS.length];
          ctx.fillRect((x + 0.15 + item * 0.5) * unit, (top + 0.3 + row * 0.75) * unit,
            0.35 * unit, 0.45 * unit);
        }
      }
    }
    label(ctx, "RAYONS", (layout.width / 2) * unit, (top - 0.25) * unit, unit, COLORS.text);
  }

  function drawDoors(ctx, layout, unit) {
    const [exitX] = layout.exit;
    ctx.fillStyle = COLORS.door;
    ctx.fillRect((exitX - 0.9) * unit, 0, 1.8 * unit, 0.3 * unit);
    signBoard(ctx, "SORTIE", (exitX - 0.2) * unit, 0.9 * unit, unit, COLORS.open);
    const [, entranceY] = layout.entrance;
    ctx.fillStyle = COLORS.door;
    ctx.fillRect(0, (entranceY - 0.9) * unit, 0.3 * unit, 1.8 * unit);
    signBoard(ctx, "ENTRÉE", 1.6 * unit, (entranceY - 1.4) * unit, unit, COLORS.sign);
  }

  function drawRegister(ctx, layout, unit, register, state, frame) {
    const [, isOpen, servingId] = state;
    const lane = register.lane_x;
    const top = layout.service_y - 1.4;
    // Tapis roulant : il défile seulement si un client est servi.
    ctx.fillStyle = COLORS.belt;
    ctx.fillRect((lane - 1.15) * unit, top * unit, 0.6 * unit, 2.8 * unit);
    ctx.fillStyle = COLORS.beltLine;
    const offset = servingId ? (frame % 8) / 8 : 0;
    for (let i = 0; i < 6; i += 1) {
      ctx.fillRect((lane - 1.15) * unit, (top + ((i + offset) % 6) * 0.46) * unit, 0.6 * unit, 2);
    }
    ctx.fillStyle = COLORS.desk;
    ctx.fillRect((lane - 2.1) * unit, (top + 0.4) * unit, 0.9 * unit, 1.8 * unit);
    // Caisse fermée : le caissier reste tant que le client en cours n'a pas fini (V06).
    const cashierPresent = isOpen || Boolean(servingId);
    RF.characters.drawCashier(ctx, (lane - 1.65) * unit, (layout.service_y - 0.1) * unit, unit,
      cashierPresent, Boolean(servingId) && frame % 20 < 10);
    // Panneau : numéro de caisse + voyant ouvert/fermé.
    const color = isOpen ? COLORS.open : COLORS.closed;
    signBoard(ctx, `CAISSE ${register.id}`, (lane - 0.8) * unit, (top - 0.8) * unit, unit, color);
    if (!isOpen) {
      ctx.fillStyle = "rgba(196, 71, 58, 0.18)";
      ctx.fillRect((lane - 2.2) * unit, top * unit, 2.8 * unit, 2.8 * unit);
      signBoard(ctx, "FERMÉE", lane * unit, (layout.first_slot_y - 0.4) * unit, unit,
        COLORS.closed);
    }
  }

  function signBoard(ctx, text, centerX, centerY, unit, color) {
    ctx.font = `bold ${Math.max(9, Math.round(unit * 0.45))}px monospace`;
    const width = ctx.measureText(text).width + unit * 0.5;
    const height = unit * 0.7;
    ctx.fillStyle = color;
    ctx.fillRect(Math.round(centerX - width / 2), Math.round(centerY - height / 2), width, height);
    label(ctx, text, centerX, centerY + unit * 0.16, unit, COLORS.signText);
  }

  function label(ctx, text, x, y, unit, color) {
    ctx.font = `bold ${Math.max(9, Math.round(unit * 0.45))}px monospace`;
    ctx.fillStyle = color;
    ctx.textAlign = "center";
    ctx.fillText(text, x, y);
  }

  return { draw };
})();
