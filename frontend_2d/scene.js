// scene.js — assemblage : canvas, mise à l'échelle, commandes de lecture, HUD.
// Point d'entrée : RF.mountScene(container, data), data venant de SceneTimeline.to_dict().
window.RF = window.RF || {};

RF.mountScene = (container, data) => {
  const { layout } = data;
  const canvas = container.querySelector("canvas");
  const ctx = canvas.getContext("2d");
  const controls = bindControls(container);
  const customers = data.customers;
  let unit = 20;
  let frame = 0;
  let followedId = null;
  let lastSlider = -1;
  let lastMonitor = -1;
  let lastTime = -1;
  let dirty = true;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const eventLabels = {
    customer_arrived: "Arrivée", queue_joined: "Entre dans la file", service_started: "Début de service",
    customer_departed: "Servi et sorti", queue_switched: "Change de file", customer_abandoned: "Abandonne",
    register_opened: "Ouverture de caisse", register_closed: "Fermeture de caisse"
  };
  customers.forEach(c => {
    const option = document.createElement("option"); option.value = c.id;
    option.textContent = `Client n°${c.id}`; controls.follow.append(option);
  });
  const laneRows = layout.registers.map(r => {
    const row = document.createElement("div"); row.className = "rf-lane";
    const name = document.createElement("b"); name.textContent = `Caisse ${r.id}`;
    const status = document.createElement("span"); row.append(name, status); controls.lanes.append(row);
    return {id:r.id, row, status};
  });

  function resize() { // V09 : la scène garde ses proportions à toutes les largeurs
    const ratio = window.devicePixelRatio || 1;
    const width = Math.min(container.querySelector(".rf-map").clientWidth, 480 * layout.width / layout.height);
    unit = width / layout.width;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${unit * layout.height}px`;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(unit * layout.height * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    dirty = true;
    ctx.imageSmoothingEnabled = false; // pixels nets
  }

  function render(player) {
    const t = player.time;
    if (t === lastTime && !dirty) return;
    lastTime = t; dirty = false;
    frame = reducedMotion ? 0 : Math.floor(t * 120);
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
    updateHud(player, registerStates);
  }

  function updateHud(player, registerStates) {
    const t = player.time;
    controls.clock.textContent = formatMinutes(t);
    if (Math.abs(t - lastMonitor) >= .08 || t === 0 || !player.playing) {
      const past = data.events.filter(e => e.time <= t);
      const arrivals = past.filter(e => e.type === "customer_arrived").length;
      const exits = past.filter(e => e.type === "customer_departed" || e.type === "customer_abandoned").length;
      controls.inStore.textContent = arrivals - exits;
      controls.served.textContent = past.filter(e => e.type === "customer_departed").length;
      controls.abandoned.textContent = past.filter(e => e.type === "customer_abandoned").length;
      const queues = Object.fromEntries(layout.registers.map(r => [r.id, 0]));
      past.forEach(e => {
        if (e.type === "queue_joined") queues[e.register_id]++;
        if (e.type === "service_started" || e.type === "customer_abandoned") queues[e.register_id]--;
        if (e.type === "queue_switched") {queues[e.register_id]--; queues[e.target_register_id]++;}
      });
      laneRows.forEach(({id,row,status}) => {
        const [,open,serving] = registerStates[id]; row.dataset.open = open;
        status.textContent = `${open ? (serving ? "En service" : "Disponible") : (serving ? "Termine son client" : "Fermée")} / ${queues[id]} en file`;
      });
      const latest = past.at(-1);
      controls.lastEvent.textContent = latest ? `${formatMinutes(latest.time)} : ${eventLabels[latest.type]}${latest.customer_id != null ? " / client " + latest.customer_id : " / caisse " + latest.register_id}` : "Aucun événement pour l'instant.";
      lastMonitor = t;
    }
    controls.empty.hidden = t > 0;
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
  player.setSpeed(5);
  controls.next.addEventListener("click", () => {
    player.pause(); const next = data.events.find(e => e.time > player.time);
    player.seek(next ? next.time : data.end_time);
  });
  controls.follow.addEventListener("change", () => {
    followedId = controls.follow.value ? Number(controls.follow.value) : null; dirty = true;
  });
  container.addEventListener("keydown", e => {
    if (["INPUT", "SELECT", "BUTTON"].includes(e.target.tagName)) return;
    if (e.code === "Space") {e.preventDefault(); player.playing ? player.pause() : player.play(); dirty = true;}
    if (e.code === "ArrowRight" || e.code === "ArrowLeft") {
      e.preventDefault(); player.pause(); player.seek(player.time + (e.code === "ArrowRight" ? 1 : -1));
    }
  });
  document.addEventListener("visibilitychange", () => {if (document.hidden) {player.pause(); dirty = true;}});

  controls.play.addEventListener("click", () => {player.playing ? player.pause() : player.play(); dirty = true;});
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
    controls.follow.value = followedId === null ? "" : String(followedId); dirty = true;
  });
  window.addEventListener("resize", resize);
  new ResizeObserver(resize).observe(container.querySelector(".rf-map"));
  resize();
  return player;
};

function bindControls(container) {
  const find = (role) => container.querySelector(`[data-role="${role}"]`);
  return {
    play: find("play"), restart: find("restart"), slider: find("slider"), speed: find("speed"),
    clock: find("clock"), inStore: find("in-store"), served: find("served"),
    abandoned: find("abandoned"), followed: find("followed"),
    follow: find("follow"), next: find("next"), lanes: find("lanes"), lastEvent: find("last-event"), empty: find("empty"),
  };
}

function formatMinutes(minutes) {
  const whole = Math.floor(minutes);
  const seconds = Math.floor((minutes - whole) * 60);
  return `${whole} min ${String(seconds).padStart(2, "0")} s`;
}
