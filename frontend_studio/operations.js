// Index du journal : statistiques en direct et projection sans lecture du futur.
RF.Operations = class {
  constructor(data) {
    this.rows = [];
    this.horizon = Infinity;
    let lastExit = 0,
      waitSum = 0;
    let arrivals = 0,
      starts = 0,
      served = 0,
      abandoned = 0,
      busyMinutes = 0,
      availableMinutes = 0,
      previous = 0;
    const opened = Object.fromEntries(
      [1, 2, 3, 4, 5].map((r) => [r, r <= data.initially_open]),
    );
    const serving = {},
      arrived = {},
      startTimes = {},
      waits = [];
    for (const e of data.events) {
      const busy = Object.values(serving).filter((x) => x != null).length;
      const available = Object.keys(opened).filter(
        (r) => opened[r] || serving[r] != null,
      ).length;
      busyMinutes += (e.time - previous) * busy;
      availableMinutes += (e.time - previous) * available;
      previous = e.time;
      const id = e.customer_id,
        r = e.register_id;
      if (e.type === "customer_arrived") {
        arrivals++;
        arrived[id] = e.time;
      }
      if (e.type === "service_started") {
        starts++;
        serving[r] = id;
        startTimes[id] = e.time;
      }
      if (e.type === "customer_departed") {
        served++;
        serving[r] = null;
        const wait = startTimes[id] - arrived[id];
        waits.push(wait);
        waitSum += wait;
        lastExit = e.time;
      }
      if (e.type === "customer_abandoned") {
        abandoned++;
        lastExit = e.time;
      }
      if (e.type === "register_opened") opened[r] = true;
      if (e.type === "register_closed") opened[r] = false;
      this.rows.push({
        time: e.time,
        arrivals,
        starts,
        served,
        abandoned,
        waiting: arrivals - starts - abandoned,
        busyMinutes,
        availableMinutes,
        busy: Object.values(serving).filter((x) => x != null).length,
        available: Object.keys(opened).filter(
          (r) => opened[r] || serving[r] != null,
        ).length,
        completedWaits: waits.length,
        waitSum,
      });
    }
    // Un journal partiel ne doit pas figer les compteurs à sa première sortie.
    const expected =
      data.customers?.length ??
      (Object.keys(data.people || {}).length || arrivals);
    if (expected > 0 && served + abandoned === expected)
      this.horizon = lastExit;
    this.waits = waits;
  }
  indexAt(time) {
    let low = 0,
      high = this.rows.length;
    while (low < high) {
      const mid = (low + high) >> 1;
      if (this.rows[mid].time <= time) low = mid + 1;
      else high = mid;
    }
    return low - 1;
  }
  rowAt(time) {
    return (
      this.rows[this.indexAt(time)] || {
        time: 0,
        arrivals: 0,
        starts: 0,
        served: 0,
        abandoned: 0,
        waiting: 0,
        busyMinutes: 0,
        availableMinutes: 0,
        busy: 0,
        available: 0,
        completedWaits: 0,
        waitSum: 0,
      }
    );
  }
  at(time) {
    time = Math.min(time, this.horizon);
    const row = this.rowAt(time),
      past = this.rowAt(Math.max(0, time - 5)),
      dt = Math.min(5, time);
    const busy = row.busyMinutes + (time - row.time) * row.busy;
    const available = row.availableMinutes + (time - row.time) * row.available;
    const waits = this.waits.slice(0, row.completedWaits).sort((a, b) => a - b);
    const position = (waits.length - 1) * 0.9,
      lo = Math.floor(position),
      hi = Math.ceil(position);
    return {
      ...row,
      occupation: available ? (100 * busy) / available : 0,
      meanWait: waits.length ? row.waitSum / waits.length : null,
      p90: waits.length
        ? waits[lo] + (waits[hi] - waits[lo]) * (position - lo)
        : null,
      shareCompletedUnderFivePercent: row.served
        ? (100 * waits.filter((w) => w <= 5).length) / row.served
        : null,
      throughput: dt ? ((row.served - past.served) / dt) * 60 : 0,
      projection:
        time >= 5
          ? Math.max(
              0,
              row.waiting +
                (row.arrivals -
                  past.arrivals -
                  row.starts +
                  past.starts -
                  row.abandoned +
                  past.abandoned),
            )
          : null,
    };
  }
  history(time) {
    const from = Math.max(0, time - 20),
      points = [{ ...this.rowAt(from), time: from }];
    const end = this.indexAt(time);
    for (let i = Math.max(0, this.indexAt(from) + 1); i <= end; i++)
      points.push(this.rows[i]);
    points.push({ ...this.rowAt(time), time });
    return points;
  }
};

// Dessin borné au préfixe connu, au plus 20 minutes de journal.
RF.drawFlow = (canvas, ops, time) => {
  const rect = canvas.getBoundingClientRect(),
    ratio = Math.min(devicePixelRatio || 1, 2);
  const w = Math.max(1, rect.width),
    h = Math.max(1, rect.height);
  if (
    canvas.width !== Math.round(w * ratio) ||
    canvas.height !== Math.round(h * ratio)
  ) {
    canvas.width = Math.round(w * ratio);
    canvas.height = Math.round(h * ratio);
  }
  const c = canvas.getContext("2d");
  c.setTransform(ratio, 0, 0, ratio, 0, 0);
  c.clearRect(0, 0, w, h);
  const points = ops.history(time),
    from = Math.max(0, time - 20),
    span = Math.max(1, time - from);
  const max = Math.max(
    5,
    ...points.map((p) => p.waiting),
    ...points.map((p) => p.busy),
  );
  const x = (t) => 32 + ((t - from) / span) * (w - 45),
    y = (n) => h - 25 - (n / max) * (h - 40);
  c.font = "11px system-ui";
  c.fillStyle = "#5c7486";
  for (const n of [0, max]) {
    c.fillText(String(n), 5, y(n) + 4);
    c.strokeStyle = "#e4edf2";
    c.beginPath();
    c.moveTo(30, y(n));
    c.lineTo(w - 10, y(n));
    c.stroke();
  }
  for (const [key, color] of [
    ["waiting", "#c19a50"],
    ["busy", "#238e7d"],
  ]) {
    c.beginPath();
    c.strokeStyle = color;
    c.lineWidth = 2;
    points.forEach((p, i) => {
      if (!i) c.moveTo(x(p.time), y(p[key]));
      else {
        c.lineTo(x(p.time), y(points[i - 1][key]));
        c.lineTo(x(p.time), y(p[key]));
      }
    });
    c.stroke();
  }
  c.fillStyle = "#5c7486";
  c.fillText(RF.minutes(from), 32, h - 5);
  c.textAlign = "right";
  c.fillText(RF.minutes(time), w - 12, h - 5);
  c.textAlign = "left";
};
