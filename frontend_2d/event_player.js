// event_player.js — horloge de lecture (minutes simulées).
// Le facteur de vitesse accélère seulement la LECTURE : les trajectoires sont
// déjà calculées, donc pause, reprise, x1-x5 et retour en arrière ne changent
// jamais le résultat (chaque image est recalculée à partir du temps seul).
window.RF = window.RF || {};

RF.Player = class {
  static MINUTES_PER_SECOND_AT_X1 = 0.5; // x1 : 1 minute simulée = 2 secondes réelles
  static SPEEDS = [1, 2, 3, 4, 5];

  constructor(endTime, onChange) {
    this.endTime = endTime;
    this.time = 0;
    this.speed = 1;
    this.playing = false;
    this.onChange = onChange;
    this.lastFrame = null;
    requestAnimationFrame((now) => this.loop(now));
  }

  loop(now) {
    if (this.playing && this.lastFrame !== null) {
      const elapsedSeconds = Math.min(0.1, (now - this.lastFrame) / 1000); // onglet en veille
      this.seek(this.time + elapsedSeconds * this.speed * RF.Player.MINUTES_PER_SECOND_AT_X1);
      if (this.time >= this.endTime) this.pause();
    }
    this.lastFrame = now;
    this.onChange(this);
    requestAnimationFrame((next) => this.loop(next));
  }

  play() {
    if (this.time >= this.endTime) this.time = 0;
    this.playing = true;
  }

  pause() { this.playing = false; }

  restart() { this.seek(0); this.play(); }

  seek(time) { this.time = Math.min(this.endTime, Math.max(0, time)); }

  setSpeed(speed) {
    if (!RF.Player.SPEEDS.includes(speed)) throw new Error(`Vitesse inconnue : x${speed}`);
    this.speed = speed;
  }
};
