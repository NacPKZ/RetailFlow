// Lecture des événements du moteur. Ce module ne prend aucune décision d'affectation.
RF.Replay = class {
  constructor(data) { this.data = data; this.reset(); }
  reset() {
    this.index = 0; this.time = -1;
    this.queues = Object.fromEntries([1,2,3,4,5].map(r => [r, []]));
    this.open = Object.fromEntries([1,2,3,4,5].map(r => [r, r <= this.data.initially_open]));
    this.serving = Object.fromEntries([1,2,3,4,5].map(r => [r, null]));
    this.status = {}; this.arrivals = 0; this.served = 0; this.abandoned = 0;
  }
  at(time) {
    if (time < this.time) this.reset();
    while (this.index < this.data.events.length && this.data.events[this.index].time <= time) {
      const e = this.data.events[this.index++]; const r = e.register_id, c = e.customer_id;
      const remove = () => {const i=this.queues[r].indexOf(c); if(i>=0) this.queues[r].splice(i,1);};
      if(e.type === 'customer_arrived') {this.arrivals++; this.status[c]='waiting';}
      if(e.type === 'queue_joined') this.queues[r].push(c);
      if(e.type === 'service_started') {remove(); this.serving[r]=c; this.status[c]='service';}
      if(e.type === 'customer_departed') {this.serving[r]=null; this.status[c]='served'; this.served++;}
      if(e.type === 'customer_abandoned') {remove(); this.status[c]='abandoned'; this.abandoned++;}
      if(e.type === 'queue_switched') {remove(); this.queues[e.target_register_id].push(c);}
      if(e.type === 'register_opened') this.open[r]=true;
      if(e.type === 'register_closed') this.open[r]=false;
    }
    this.time=time;
    const waiting = Object.values(this.queues).flat();
    const waits = waiting.map(c => Math.max(0,time-this.data.people[c].arrival_time));
    return {queues:this.queues,open:this.open,serving:this.serving,status:this.status,
      arrivals:this.arrivals,served:this.served,abandoned:this.abandoned,waiting:waiting.length,
      present:this.arrivals-this.served-this.abandoned, inService:Object.values(this.serving).filter(x=>x!==null).length,
      longest:waits.length ? Math.max(...waits) : 0, overFive:waits.filter(w=>w>5).length,
      recent:this.data.events.slice(Math.max(0,this.index-5),this.index).reverse()};
  }
};
RF.eventLabels = {customer_arrived:'Arrivée',queue_joined:'Entrée en file',service_started:'Début de service',
  customer_departed:'Servi et sorti',customer_abandoned:'Abandon',queue_switched:'Changement de file',
  register_opened:'Ouverture de caisse',register_closed:'Fermeture de caisse'};
RF.minutes = n => `${Math.floor(n)}:${String(Math.floor((n%1)*60)).padStart(2,'0')}`;
RF.colours = ['#3e8bd6','#29a98b','#d4a34c','#9976cc','#d27883'];
