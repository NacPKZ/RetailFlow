// Tests de logique du lecteur sans navigateur : données et commandes seulement.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
class Element {
  constructor() {this.children=[];this.handlers={};this.style={};this.dataset={};this.clientWidth=900;this.value='';}
  append(...children) {this.children.push(...children);}
  addEventListener(name, fn) {this.handlers[name]=fn;}
  fire(name, data={}) {this.handlers[name]?.(data);}
  getBoundingClientRect() {return {left:0,top:0};}
}
const roles=Object.fromEntries(['play','restart','slider','speed','clock','in-store','served','abandoned',
  'followed','follow','next','lanes','last-event','empty'].map(r=>[r,new Element()]));
const canvas=new Element();
const ctx=new Proxy({}, {get:(target,key)=>target[key] || (()=>{}),set:(target,key,value)=>(target[key]=value,true)});
ctx.measureText=()=>({width:20}); canvas.getContext=()=>ctx;
const map=new Element();
const container=new Element();
container.querySelector=selector=>selector==='canvas' ? canvas : selector==='.rf-map' ? map : roles[selector.match(/data-role="(.*?)"/)[1]];
const environment={console,document:new Element(),ResizeObserver:class {observe() {}},
  requestAnimationFrame:()=>{},window:null};
environment.window=environment;environment.matchMedia=()=>({matches:false});
environment.addEventListener=()=>{};environment.document.createElement=()=>new Element();
vm.createContext(environment);
for(const file of ['animations.js','event_player.js','characters.js','map.js','scene.js']) {
  vm.runInContext(fs.readFileSync(path.join(root,'frontend_2d',file),'utf8'),environment);
}
const events=[
  {time:1,type:'customer_arrived',customer_id:1},
  {time:1,type:'queue_joined',customer_id:1,register_id:1},
  {time:1,type:'service_started',customer_id:1,register_id:1},
  {time:2,type:'customer_arrived',customer_id:2},
  {time:2,type:'queue_joined',customer_id:2,register_id:1},
  {time:3,type:'queue_switched',customer_id:2,register_id:1,target_register_id:2},
  {time:4,type:'customer_abandoned',customer_id:2,register_id:2},
  {time:5,type:'customer_departed',customer_id:1,register_id:1},
];
const data={layout:{width:24,height:20,main_aisle_y:15,service_y:4,first_slot_y:6,
  entrance:[0,15],exit:[23,0],registers:[{id:1,lane_x:5},{id:2,lane_x:10}]},
  end_time:6,customers:[],registers:{1:[[0,true,null],[1,true,1],[5,true,null]],2:[[0,true,null]]},
  served_at:{1:5},abandoned_at:{2:4},events};
const player=environment.RF.mountScene(container,data);
const render=()=>player.onChange(player);
render();assert.equal(roles['in-store'].textContent,0);
assert.equal(player.speed,5);
assert.equal(canvas.style.height,'480px');
roles.next.fire('click');render();assert.equal(player.time,1);assert.equal(roles['in-store'].textContent,1);
player.seek(3);render();assert.equal(roles['in-store'].textContent,2);
assert.match(roles.lanes.children[0].children[1].textContent,/0 en file/);
assert.match(roles.lanes.children[1].children[1].textContent,/1 en file/);
player.seek(4);render();assert.equal(roles.abandoned.textContent,1);assert.equal(roles['in-store'].textContent,1);
player.seek(6);render();assert.equal(roles.served.textContent,1);assert.equal(roles['in-store'].textContent,0);
player.seek(1);render();assert.equal(roles.abandoned.textContent,0);assert.equal(roles.served.textContent,0);
roles.speed.value='20';roles.speed.fire('change');assert.equal(player.speed,20);
roles.play.fire('click');render();assert.equal(player.playing,true);
roles.play.fire('click');render();assert.equal(player.playing,false);assert.equal(roles.play.textContent,'▶ Lecture');
player.seek(-10);assert.equal(player.time,0);player.seek(100);assert.equal(player.time,6);
assert.throws(()=>player.setSpeed(99));
console.log('Lecteur JS : pause, reprise, avance, retour, x20, caisses et conservation des clients OK.');
