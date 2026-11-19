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
    return {queues:Object.fromEntries(Object.entries(this.queues).map(([r,q])=>[r,[...q]])),
      open:{...this.open},serving:{...this.serving},status:{...this.status},
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

// L'inspecteur n'expose que le préfixe connu du journal, jamais les sorties futures.
RF.clientAt = (data, id, time, state) => {
  const events=data.events.filter(e=>e.customer_id===id && e.time<=time);
  const arrival=events.find(e=>e.type==='customer_arrived');
  const start=events.find(e=>e.type==='service_started');
  const end=events.find(e=>['customer_departed','customer_abandoned'].includes(e.type));
  const lane=Object.keys(state.queues).find(r=>state.queues[r].includes(id))
    || Object.keys(state.serving).find(r=>state.serving[r]===id);
  const last=events.filter(e=>e.register_id!=null).at(-1);
  return {events,arrival:arrival?.time??null,start:start?.time??null,end:end?.time??null,
    register:lane?Number(lane):last?.target_register_id??last?.register_id??null,
    position:lane&&state.queues[lane].includes(id)?state.queues[lane].indexOf(id)+1:null,
    switches:events.filter(e=>e.type==='queue_switched').length,
    wait:arrival?Math.max(0,(start?.time??end?.time??time)-arrival.time):0};
};
// Le curseur Python est une consigne ponctuelle, pas une position imposée à chaque rerun.
RF.cursorTime = (data,saved) => {
  const cursor=data.cursor||{},fresh=cursor.token && cursor.token!==saved.cursorToken;
  return Math.max(0,Math.min(data.end_time,Number(fresh?cursor.time:saved.time)||0));
};
// Premier franchissement strict du seuil, même si x50 saute plusieurs événements.
RF.waitCrossing = (data,from,to,threshold=5) => {
  let first=null;
  for(const p of Object.values(data.people)) {
    const crossing=p.arrival_time+threshold+1e-7;
    const end=p.service_start??p.abandoned_at??Infinity;
    if(crossing>from && crossing<=to && crossing<end && (first===null||crossing<first))first=crossing;
  }
  return first;
};
