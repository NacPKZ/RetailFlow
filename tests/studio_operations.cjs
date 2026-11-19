// Statistiques du journal et caméra : lecture préfixe, indépendance de la vitesse.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const env={RF:{}};vm.createContext(env);
for(const file of ['operations.js','painter.js'])vm.runInContext(fs.readFileSync(`frontend_studio/${file}`,'utf8'),env);
const data={initially_open:2,events:[
  {time:0,type:'customer_arrived',customer_id:1},
  {time:0,type:'queue_joined',customer_id:1,register_id:1},
  {time:0,type:'service_started',customer_id:1,register_id:1},
  {time:1,type:'customer_arrived',customer_id:2},
  {time:1,type:'queue_joined',customer_id:2,register_id:1},
  {time:2,type:'register_closed',register_id:1},
  {time:4,type:'customer_departed',customer_id:1,register_id:1},
  {time:6,type:'customer_abandoned',customer_id:2,register_id:1},
  {time:9,type:'register_opened',register_id:1},
]};
const ops=new env.RF.Operations(data);
assert.equal(ops.at(1).meanWait,null);assert.equal(ops.at(1).projection,null);
assert.equal(ops.at(3).occupation,50); // caisse fermée, service toujours mobilisé.
assert.equal(ops.at(4).meanWait,0);assert.equal(ops.at(4).p90,0);
assert.equal(ops.at(6).occupation,40); // 4 min de service / 10 caisse-min.
assert.equal(ops.at(10).occupation,40); // fin à la dernière sortie, commande tardive exclue.
assert.equal(ops.at(1).abandoned,0);assert.equal(ops.at(1).served,0);
assert.ok(ops.history(3).every(r=>r.time<=3));
const prefix=new env.RF.Operations({initially_open:2,events:data.events.slice(0,6)});
// Un préfixe ne fige pas ses indicateurs en attendant les sorties suivantes.
assert.equal(prefix.horizon,Infinity);
assert.equal(JSON.stringify(ops.at(1)),JSON.stringify(prefix.at(1)));
const serial=JSON.stringify(ops.at(3));for(const t of [6,1,4,2,6])ops.at(t);
assert.equal(JSON.stringify(ops.at(3)),serial);
const painter=new env.RF.StorePainter({getContext:()=>({})},{layout:{width:24,height:24}});
painter.width=1000;painter.height=600;
painter.zoomBy(2,{x:800,y:200});
const before=painter.toWorld(800,200);painter.zoomBy(1.1,{x:800,y:200});
const after=painter.toWorld(800,200);
assert.ok(Math.abs(before.x-after.x)<1e-10&&Math.abs(before.y-after.y)<1e-10);
painter.pan={x:1e5,y:-1e5};painter.clampCamera();
assert.ok(painter.toWorld(0,0).x>=-1e-10&&painter.toWorld(1000,600).y<=24+1e-10);
painter.focus(100,-100,3);assert.ok(Math.abs(painter.pan.x)<=1000);
painter.resetCamera();assert.equal(painter.zoom,1);assert.equal(painter.pan.x,0);
console.log('V7 : statistiques temporelles, ressources, préfixe, projection et caméra bornée OK.');
