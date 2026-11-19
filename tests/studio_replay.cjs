// Invariants du lecteur utilisé par l'atelier, indépendamment du rendu.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const env={RF:{}};vm.createContext(env);vm.runInContext(fs.readFileSync(path.join(__dirname,'../frontend_studio/replay.js'),'utf8'),env);
const data={initially_open:2,people:{1:{arrival_time:0},2:{arrival_time:1}},events:[
  {time:0,type:'customer_arrived',customer_id:1},{time:0,type:'queue_joined',customer_id:1,register_id:1},
  {time:0,type:'service_started',customer_id:1,register_id:1},
  {time:1,type:'customer_arrived',customer_id:2},{time:1,type:'queue_joined',customer_id:2,register_id:1},
  {time:3,type:'queue_switched',customer_id:2,register_id:1,target_register_id:2},
  {time:4,type:'register_closed',register_id:1},
  {time:7,type:'customer_abandoned',customer_id:2,register_id:2},
  {time:9,type:'customer_departed',customer_id:1,register_id:1}]};
const replay=new env.RF.Replay(data);
let s=replay.at(2);assert.equal(s.waiting,1);assert.equal(s.present,2);assert.equal(s.longest,1);
s=replay.at(6.1);assert.equal(s.open[1],false);assert.equal(s.serving[1],1);assert.equal(s.overFive,1);assert.deepEqual(Array.from(s.queues[2]),[2]);
s=replay.at(9);assert.equal(s.present,0);assert.equal(s.served,1);assert.equal(s.abandoned,1);
s=replay.at(1);assert.equal(s.present,2);assert.equal(s.abandoned,0);assert.equal(s.open[1],true);
for(const time of [0,1,3,4,6,7,8,9]){const s=replay.at(time);assert.equal(s.arrivals,s.waiting+s.inService+s.served+s.abandoned);}
assert.equal(env.RF.minutes(1.5),'1:30');
console.log('Atelier : temps, compteurs, transfert, fermeture, abandon et retour arrière OK.');
// Instantanés indépendants, recherche sans divulgation et curseur ponctuel.
const earlier=replay.at(2),serialized=JSON.stringify(earlier);replay.at(9);
assert.equal(JSON.stringify(earlier),serialized);
const view=env.RF.clientAt(data,2,2,replay.at(2));
assert.equal(view.start,null);assert.equal(view.end,null);assert.equal(view.switches,0);assert.equal(view.position,1);
assert.equal(env.RF.clientAt(data,2,8,replay.at(8)).end,7);
assert.equal(env.RF.cursorTime({end_time:20,cursor:{token:'a',time:3}},{time:12,cursorToken:'a'}),12);
assert.equal(env.RF.cursorTime({end_time:20,cursor:{token:'b',time:3}},{time:12,cursorToken:'a'}),3);
const crossingData={people:{1:{arrival_time:0,service_start:6},2:{arrival_time:1,abandoned_at:4}}};
assert.ok(env.RF.waitCrossing(crossingData,4,9)>5);
assert.equal(env.RF.waitCrossing(crossingData,6,9),null);
console.log('V6.1 : instantanés indépendants, inspecteur temporel, curseur ponctuel et seuil x50 OK.');
