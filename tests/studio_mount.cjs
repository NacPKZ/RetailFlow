// Test unitaire du cycle de montage, sans navigateur ni mesure visuelle.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const data=JSON.parse(fs.readFileSync(0,'utf8')),before=JSON.stringify(data);
const context=new Proxy({}, {get:(o,k)=>o[k]??(()=>{}),set:(o,k,v)=>(o[k]=v,true)});
class Element {
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.attrs={};
    this.style={setProperty(){}};this.value='';this.checked=false;this.disabled=false;this.hidden=false;
    this.classes=new Set();this.classList={add:(...xs)=>xs.forEach(x=>this.classes.add(x)),
      remove:(...xs)=>xs.forEach(x=>this.classes.delete(x)),contains:x=>this.classes.has(x),
      toggle:(x,on)=>{const yes=on??!this.classes.has(x);yes?this.classes.add(x):this.classes.delete(x);return yes;}};
    this.listeners=new Map();
  }
  setAttribute(k,v){this.attrs[k]=v;}
  append(...xs){this.children.push(...xs);}
  replaceChildren(...xs){this.children=[...xs];}
  get options(){return this.children;}
  getContext(){return context;}
  getBoundingClientRect(){return {left:0,top:0,width:1000,height:650};}
  querySelectorAll(){return this.children;}
  addEventListener(k,v){this.listeners.set(k,v);}
  removeEventListener(k){this.listeners.delete(k);}
  focus(){}
  click(){if(!this.disabled)this.onclick?.({detail:0});}
}
const html=fs.readFileSync('frontend_studio/studio.html','utf8'),controls={};
for(const match of html.matchAll(/data-role="([^"]+)"/g))controls[match[1]]=new Element();
controls.heat.checked=true;controls.motion.checked=true;controls['minimap-toggle'].checked=true;
controls['guide-steps'].children=Array.from({length:5},()=>new Element('button'));
const root=new Element(),canvas=new Element('canvas'),head=new Element('p');
root.querySelector=selector=>selector==='canvas'?canvas:selector==='.studio-head p'?head:
  controls[selector.match(/data-role="([^"]+)"/)?.[1]]??null;
const storage=new Map(),document=new Element('document');
document.createElement=tag=>new Element(tag);document.createTextNode=text=>({textContent:text});
let callback=null,cancelled=false;
const env={RF:{},console,Math,JSON,devicePixelRatio:1,performance:{now:()=>0},
  window:{matchMedia:()=>({matches:false})},document,crypto:{randomUUID:()=> 'test-command'},
  sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
  requestAnimationFrame:cb=>(callback=cb,1),cancelAnimationFrame:()=>cancelled=true,
  ResizeObserver:class{observe(){}disconnect(){}},setTimeout:()=>1,clearTimeout(){},
};
vm.createContext(env);
vm.runInContext(fs.readFileSync('frontend_2d/animations.js','utf8').replace('window.RF = window.RF || {};',''),env);
for(const name of ['replay.js','operations.js','painter.js','inspector.js','studio.js'])
  vm.runInContext(fs.readFileSync(`frontend_studio/${name}`,'utf8'),env);
let command=null;
const cleanup=env.RF.mountStudio(root,data,a=>command=a);
callback(0);assert.equal(controls.waiting.textContent,'0');
controls.peak.click();callback(120);
assert.ok(Number(controls.waiting.textContent)>6);
assert.ok(controls.projection.textContent.includes('clients'));
controls['layout-scene'].click();callback(240);assert.ok(root.classList.contains('focus-scene'));
controls['layout-all'].click();assert.ok(!root.classList.contains('focus-scene'));
controls['client-id'].value=String(data.customers[0].id);
controls['client-search'].onsubmit({preventDefault(){}});callback(360);
assert.equal(controls.follow.disabled,false);controls.follow.click();callback(480);
assert.equal(controls.follow.attrs['aria-pressed'],'true');
controls.motion.checked=false;controls.motion.onchange();assert.ok(root.classList.contains('reduced-decoration'));
controls['minimap-toggle'].checked=false;controls['minimap-toggle'].onchange();
assert.ok(controls['minimap-button'].hidden);
controls.speed.value='50';controls.speed.onchange();controls.play.click();
for(let i=1;i<=20;i++)callback(480+i*16);
assert.ok(controls.clock.textContent);assert.equal(command,null);
controls['open-next'].click();assert.equal(command.kind,'register');
assert.equal(command.run_id,data.run_id);assert.equal(command.revision,data.revision);
cleanup();assert.ok(cancelled);assert.equal(root.listeners.size,0);assert.equal(document.listeners.size,0);
assert.equal(JSON.stringify(data),before);
const saved=JSON.parse(storage.values().next().value);assert.equal(saved.options.motion,false);
assert.equal(saved.minimap,false);
console.log('V7 : montage, lecture x50, contrôles, suivi, commande Python et nettoyage OK.');
