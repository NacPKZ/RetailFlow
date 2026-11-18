// scene.js — assemblage : canvas, mise à l'échelle, commandes de lecture, HUD.
// Point d'entrée : RF.mountScene(container, data), data venant de SceneTimeline.to_dict().
window.RF = window.RF || {};

RF.mountScene = (container, data) => {
  const { layout } = data;
  const canvas = container.querySelector("canvas");
  const ctx = canvas.getContext("2d");
  const controls = bindControls(container);
  const customers = data.customers;
  const served = Object.values(data.served_at);
  const abandoned = Object.values(data.abandoned_at);
  let unit = 20;
  let frame = 0;
  let followedId = null;
  let lastSlider = -1;

  function resize() { // V09 : la scène garde ses proportions à toutes les largeurs
    const ratio = window.devicePixelRatio || 1;
    const width = container.clientWidth;
    unit = width / layout.width;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${unit * layout.height}px`;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(unit * layout.height * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.imageSmoothingEnabled = false; // pixels nets
  }

  function render(player) {
    frame += 1;
    const t = player.time;
    const registerStates = {};
    Object.entries(data.registers).forEach(([id, states]) => {
      registerStates[id] = RF.anim.registerAt(states, t);
    });
    RF.map.draw(ctx, layout, unit, registerStates, frame);
    const visible = [];
    customers.forEach((customer) => {
      const position = RF.anim.sample(customer.keyframes, t);
      if (position) visible.push({ id: customer.id, ...position });
    });
    visible.sort((a, b) => a.y - b.y) // ceux du fond d'abord
      .forEach((c) => RF.characters.drawCustomer(ctx, c, c.x * unit, c.y * unit, unit, frame,
        c.id === followedId));
    updateHud(player, visible);
  }

  function updateHud(player, visible) {
    const t = player.time;
    controls.clock.textContent = formatMinutes(t);
    controls.inStore.textContent = visible.length;
    controls.served.textContent = served.filter((time) => time <= t).length;
    controls.abandoned.textContent = abandoned.filter((time) => time <= t).length;
    controls.play.textContent = player.playing ? "⏸ Pause" : "▶ Lecture";
    const sliderValue = Math.round((t / data.end_time) * 1000);
    if (sliderValue !== lastSlider && document.activeElement !== controls.slider) {
      controls.slider.value = sliderValue;
      lastSlider = sliderValue;
    }
    controls.followed.textContent = followedId === null ? "aucun (cliquez sur un client)"
      : `client n°${followedId}`;
  }

  const player = new RF.Player(data.end_time, render);

  controls.play.addEventListener("click", () => (player.playing ? player.pause() : player.play()));
  controls.restart.addEventListener("click", () => player.restart());
  controls.slider.addEventListener("input", () => {
    player.pause();
    player.seek((controls.slider.value / 1000) * data.end_time);
  });
  controls.speed.addEventListener("change", () => player.setSpeed(Number(controls.speed.value)));
  canvas.addEventListener("click", (event) => { // suivi d'un client
    const box = canvas.getBoundingClientRect();
    const x = (event.clientX - box.left) / unit;
    const y = (event.clientY - box.top) / unit;
    let closest = null;
    customers.forEach((customer) => {
      const position = RF.anim.sample(customer.keyframes, player.time);
      if (!position) return;
      const distance = Math.hypot(position.x - x, position.y - 0.3 - y);
      if (distance < 0.8 && (!closest || distance < closest.distance)) {
        closest = { id: customer.id, distance };
      }
    });
    followedId = closest ? closest.id : null;
  });
  window.addEventListener("resize", resize);
  resize();
  return player;
};

function bindControls(container) {
  const find = (role) => container.querySelector(`[data-role="${role}"]`);
  return {
    play: find("play"), restart: find("restart"), slider: find("slider"), speed: find("speed"),
    clock: find("clock"), inStore: find("in-store"), served: find("served"),
    abandoned: find("abandoned"), followed: find("followed"),
  };
}

function formatMinutes(minutes) {
  const whole = Math.floor(minutes);
  const seconds = Math.floor((minutes - whole) * 60);
  return `${whole} min ${String(seconds).padStart(2, "0")} s`;
}
