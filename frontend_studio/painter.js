// Dessin du magasin. La géométrie de la caméra ne modifie aucun événement métier.
RF.StorePainter = class {
  constructor(canvas,data) {
    this.canvas=canvas; this.ctx=canvas.getContext('2d');this.data=data;
    this.width=0;this.height=0;this.zoom=1;this.pan={x:0,y:0};this.people=[];
    this.options={heat:true,labels:false,trails:false};this.selected=null;this.hover=null;this.drag=null;
    this.bg=null;
  }
  resize() {
    const rect=this.canvas.getBoundingClientRect(); const ratio=Math.min(devicePixelRatio||1,2);
    this.width=Math.max(1,rect.width);this.height=Math.max(1,rect.height);
    this.canvas.width=Math.round(this.width*ratio);this.canvas.height=Math.round(this.height*ratio);
    this.ctx.setTransform(ratio,0,0,ratio,0,0);this.bg=null;
  }
  toWorld(x,y) {
    return {x:((x-this.width/2-this.pan.x)/this.zoom+this.width/2)/this.width*this.data.layout.width,
      y:((y-this.height/2-this.pan.y)/this.zoom+this.height/2)/this.height*this.data.layout.height};
  }
  zoomBy(factor) {this.zoom=Math.max(1,Math.min(3,this.zoom*factor));if(this.zoom===1)this.pan={x:0,y:0};}
  resetCamera() {this.zoom=1;this.pan={x:0,y:0};}
  registerAt(point) {
    return this.data.layout.registers.find(r=>Math.abs(point.x-(r.lane_x-.65))<1.65 && point.y>1.8 && point.y<5.65)?.id;
  }
  laneAt(point) {
    return this.data.layout.registers.find(r=>Math.abs(point.x-r.lane_x)<1.8 && point.y>1.8 && point.y<this.data.layout.main_aisle_y-.3)?.id;
  }
  personAt(point) {
    return [...this.people].reverse().find(p=>Math.abs(p.x-point.x)<.52 && Math.abs(p.y-point.y-.1)<.7);
  }
  round(ctx,x,y,w,h,r,fill,stroke=null) {
    ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fillStyle=fill;ctx.fill();
    if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=1;ctx.stroke();}
  }
  text(ctx,text,x,y,size=14,color='#375a6b',align='left',weight=600) {
    ctx.font=`${weight} ${size}px Inter, system-ui, sans-serif`;ctx.fillStyle=color;ctx.textAlign=align;ctx.fillText(text,x,y);
  }
  background() {
    if(this.bg) return this.bg;
    const canvas=document.createElement('canvas');canvas.width=this.width;canvas.height=this.height;
    const c=canvas.getContext('2d'),w=this.width,h=this.height,ux=w/this.data.layout.width,uy=h/this.data.layout.height;
    const aisle=this.data.layout.main_aisle_y,H=this.data.layout.height;
    c.fillStyle='#e8ede8';c.fillRect(0,0,w,h);
    for(let x=0;x<24;x++)for(let y=0;y<H;y++){
      c.fillStyle=(x+y)%2?'#e9efea':'#f0f3ed';c.fillRect(x*ux,y*uy,ux+1,uy+1);
    }
    c.fillStyle='#d5e1d9';c.fillRect(0,(aisle-.5)*uy,w,1.2*uy);
    c.fillStyle='#d0dfd8';c.fillRect(0,1.1*uy,w,.7*uy);
    c.fillStyle='#33544f';c.fillRect(0,0,w,.25*uy);
    this.text(c,'CAISSES ET PAIEMENT',w/2,1.0*uy,Math.max(12,ux*.26),'#6e8d82','center');
    this.text(c,'CIRCULATION',w/2,(aisle+.3)*uy,Math.max(9,ux*.23),'#81998c','center');
    this.round(c,.35*ux,(aisle-1.2)*uy,2.5*ux,.7*uy,6,'#3d6554');
    this.text(c,'ENTRÉE →',1.6*ux,(aisle-.7)*uy,Math.max(10,ux*.25),'#fff','center');
    this.round(c,21*ux,.55*uy,2.4*ux,.7*uy,5,'#43826c');
    this.text(c,'SORTIE ↑',22.2*ux,1.04*uy,Math.max(10,ux*.24),'#fff','center');
    // Porte vitrée et barrières antivol, sans couper la circulation.
    this.round(c,.02*ux,(aisle-.45)*uy,.18*ux,.9*uy,2,'#98c2bc');
    for(const y of [aisle-.55,aisle+.55])this.round(c,.35*ux,y*uy,.12*ux,.32*uy,2,'#79918c');
    const departments=[['FRUITS & LÉGUMES','#789c66'],['ÉPICERIE','#bd9b61'],['BOISSONS','#82a4b6'],['BOULANGERIE','#c6a16c'],['HYGIÈNE','#9c9cb5']];
    const top=aisle+2.0,bottom=H-3.2;
    departments.forEach(([label,tone],i)=>{
      const x=(2.15+i*4.3)*ux,y=top*uy,width=2.6*ux,height=(bottom-top)*uy;
      this.round(c,x+3,y+5,width,height,7,'#bac9bb');
      this.round(c,x,y,width,height,7,i===0?'#9c9472':'#bdc4b8');
      this.round(c,x-.22*ux,y-.95*uy,width+.44*ux,.66*uy,4,'#fffffff0');
      this.text(c,label,x+width/2,y-.48*uy,Math.max(11,ux*.23),'#687d68','center');
      for(let row=0;row<4;row++){
        const ry=y+(.28+row*(bottom-top-.5)/4)*uy;
        c.fillStyle='#7d8b7548';c.fillRect(x,ry+1.12*uy,width,.13*uy);
        for(let item=0;item<5;item++){
          const px=x+(.18+item*.47)*ux;
          if(i===0){ // Bacs de pommes, agrumes et légumes.
            c.fillStyle='#8b7755';c.fillRect(px-.04*ux,ry,.43*ux,.95*uy);
            for(let k=0;k<3;k++){
              c.fillStyle=['#a7b869','#d4aa5f','#b66f62'][(row+k)%3];c.beginPath();c.ellipse(px+.16*ux,ry+(.2+k*.23)*uy,.12*ux,.1*ux,0,0,Math.PI*2);c.fill();
            }
          }else if(i===2){ // Bouteilles et étiquettes.
            this.round(c,px,ry+.18*uy,.3*ux,.84*uy,3,['#84a6a1','#b39577','#8ca7b2'][row%3]);
            c.fillStyle='#d8e2d9';c.fillRect(px+.08*ux,ry,.14*ux,.26*uy);c.fillStyle='#eee9da';c.fillRect(px,ry+.48*uy,.3*ux,.23*uy);
          }else if(i===3){ // Pains et paniers de boulangerie.
            c.fillStyle='#d5b077';c.beginPath();c.ellipse(px+.13*ux,ry+.55*uy,.12*ux,.47*uy,-.1,0,Math.PI*2);c.fill();
            c.strokeStyle='#b48c56';c.lineWidth=1;for(let k=0;k<3;k++){c.beginPath();c.moveTo(px+.02*ux,ry+(.3+k*.18)*uy);c.lineTo(px+.22*ux,ry+(.34+k*.18)*uy);c.stroke();}
          }else{
            c.fillStyle=[tone,'#d4bd8d','#a4b58f','#b4a6b8'][(item+row)%4];c.fillRect(px,ry+.1*uy,.32*ux,.92*uy);
            c.fillStyle='#f4f0e4';c.fillRect(px+.03*ux,ry+.36*uy,.26*ux,.23*uy);
          }
        }
      }
    });
    // Meubles froids au fond : portes vitrées, poignées et socles.
    for(let i=0;i<4;i++){
      const x=(3.6+i*4.65)*ux,y=(H-2.3)*uy;
      this.round(c,x,y,3.9*ux,1.7*uy,7,'#d3e0db','#98b5ad');
      for(let door=0;door<3;door++){
        this.round(c,x+(.15+door*1.2)*ux,y+.22*uy,1.08*ux,1.12*uy,3,'#aecbd055','#a4beb6');
        c.fillStyle='#e8f1e4';c.fillRect(x+(.3+door*1.2)*ux,y+.43*uy,.65*ux,.24*uy);
        c.fillStyle='#739b91';c.fillRect(x+(1+door*1.2)*ux,y+.63*uy,.035*ux,.35*uy);
      }
      this.text(c,['FRAIS','CRÈMERIE','SURGELÉS','PRODUITS FRAIS'][i],x+1.95*ux,y+1.57*uy,Math.max(10,ux*.22),'#6a8579','center');
    }
    // Parking de chariots et paniers, près de l'entrée.
    this.text(c,'CHARIOTS',1.15*ux,(H-1.0)*uy,Math.max(8,ux*.18),'#708575','center');
    for(let i=0;i<3;i++)this.cart(c,1.15*ux,(H-2.1-i*.65)*uy,Math.min(ux,uy)*.82,0,true);
    this.bg=canvas;return canvas;
  }
  draw(time,snapshot,selected,hover,drag) {
    if(!this.width || !this.height)return;
    this.selected=selected;this.hover=hover;this.drag=drag;
    const c=this.ctx,w=this.width,h=this.height,ux=w/this.data.layout.width,uy=h/this.data.layout.height,u=Math.min(ux,uy),aisle=this.data.layout.main_aisle_y;
    c.clearRect(0,0,w,h);c.save();c.translate(w/2+this.pan.x,h/2+this.pan.y);c.scale(this.zoom,this.zoom);c.translate(-w/2,-h/2);
    c.drawImage(this.background(),0,0,w,h);
    const model=this.data.people;
    this.data.layout.registers.forEach(r=>{
      const x=r.lane_x*ux,col=RF.colours[r.id-1],q=snapshot.queues[r.id],open=snapshot.open[r.id],cid=snapshot.serving[r.id];
      const wait=q.length ? Math.max(...q.map(id=>time-model[id].arrival_time)) : 0;
      const heat=wait>5?'#c87883':wait>2.5?'#d4ad5d':'#6fbbaa';
      this.round(c,(r.lane_x-1.8)*ux,5.7*uy,3.5*ux,(aisle-6.45)*uy,12,
        this.options.heat&&open?heat+'1a':'#ffffff20',open?col+'35':'#d5c9cc');
      if(drag?.kind==='person' && drag.target===r.id) {
        c.save();c.setLineDash([8,5]);c.strokeStyle=open?'#337b9b':'#bd6073';c.lineWidth=3;
        c.strokeRect((r.lane_x-1.8)*ux,2.2*uy,3.5*ux,(aisle-2.6)*uy);c.restore();
      }
      // Numéro et état de caisse, larges zones de clic.
      this.round(c,(r.lane_x-1.8)*ux,2.1*uy,3.4*ux,1.1*uy,10,open?'#fff':'#f7eeee',open?col+'80':'#d8b1b9');
      c.fillStyle=open?col:'#c47885';c.beginPath();c.arc((r.lane_x-1.46)*ux,2.65*uy,u*.1,0,Math.PI*2);c.fill();
      this.text(c,`CAISSE ${r.id}`,(r.lane_x-.05)*ux,2.58*uy,Math.max(12,u*.35),'#2b5267','center');
      this.text(c,open?(cid?'EN SERVICE':'OUVERTE'):(cid?'TERMINE SON CLIENT':'FERMÉE'),(r.lane_x-.05)*ux,2.98*uy,Math.max(9,u*.22),open?'#528574':'#ad6677','center');
      // Comptoir, terminal et tapis roulant.
      this.round(c,(r.lane_x-1.75)*ux,3.55*uy,1.8*ux,1.35*uy,8,'#b6c8c7');
      this.round(c,(r.lane_x-1.65)*ux,3.45*uy,1.7*ux,1.27*uy,8,'#f8fcfa','#c7d6d1');
      this.round(c,(r.lane_x-1.18)*ux,3.63*uy,.64*ux,1.45*uy,4,'#314e58');
      c.fillStyle='#52737d';
      const offset=cid&&!this.reduceMotion?(time*3)%1:0;
      for(let k=0;k<5;k++)c.fillRect((r.lane_x-1.15)*ux,(3.69+((k+offset)%5)*.26)*uy,.58*ux,1.5);
      this.round(c,(r.lane_x-1.64)*ux,3.45*uy,.43*ux,.36*uy,3,'#234d64');
      c.fillStyle=cid?'#79d6b2':'#97b4c3';c.fillRect((r.lane_x-1.58)*ux,3.5*uy,.27*ux,.13*uy);
      if(open||cid) this.person(c,(r.lane_x-1.7)*ux,4.05*uy,u*.105,0,true,'#d6ad58',false);
      if(cid) {
        c.fillStyle='#96caae';c.globalAlpha=this.reduceMotion?.5:.35+.2*Math.sin(time*5);
        c.fillRect((r.lane_x-1.22)*ux,4.1*uy,.62*ux,.14*uy);c.globalAlpha=1;
        const p=model[cid],progress=Math.max(0,Math.min(1,(time-p.service_start)/p.service_duration));
        this.round(c,(r.lane_x-.38)*ux,5.12*uy,1.2*ux,.12*uy,2,'#cfdddc');
        this.round(c,(r.lane_x-.38)*ux,5.12*uy,1.2*ux*progress,.12*uy,2,col);
      }
      this.text(c,`${q.length} en file`,x,(aisle-.9)*uy,Math.max(10,u*.27),'#73928d','center');
    });
    if(this.options.trails && selected!=null) {
      const person=this.data.customers.find(p=>p.id===selected);
      if(person){c.save();c.setLineDash([5,5]);c.lineWidth=2;c.strokeStyle='#478eaa80';c.beginPath();person.keyframes.forEach((k,i)=>i?c.lineTo(k[1]*ux,k[2]*uy):c.moveTo(k[1]*ux,k[2]*uy));c.stroke();c.restore();}
    }
    this.people=[];
    for(const person of this.data.shopping_customers||[]){if(time>=person.end)continue;const p=RF.anim.sample(person.keyframes,time);if(p)this.people.push({id:person.id,...p,shopping:true});}
    for(const person of this.data.customers){const p=RF.anim.sample(person.keyframes,time);if(p)this.people.push({id:person.id,...p});}
    this.people.sort((a,b)=>a.y-b.y).forEach(p=>{
      if(drag?.kind==='person'&&drag.id===p.id)return;
      const meta=model[p.id],waiting=snapshot.status[p.id]==='waiting',wait=Math.max(0,time-meta.arrival_time);
      const ring=this.options.heat&&waiting?(wait>5?'#cc6c7d':wait>2.5?'#ceaa53':'#4ba58e'):null;
      const x=p.x*ux,y=p.y*uy;
      c.save();c.globalAlpha=snapshot.status[p.id]==='abandoned'?.65:1;
      c.fillStyle='#3659491c';c.beginPath();c.ellipse(x,y+.25*uy,u*.32,u*.13,0,0,Math.PI*2);c.fill();
      if(ring||p.id===selected||p.id===hover){c.strokeStyle=p.id===selected?'#305c9f':ring||'#6c9bb6';c.lineWidth=p.id===selected?3:2;c.beginPath();c.ellipse(x,y+.23*uy,u*.42,u*.2,0,0,Math.PI*2);c.stroke();}
      this.person(c,x,y,u*.115,p.id,false,RF.colours[p.id%5],p.moving&&!this.reduceMotion?Math.sin(time*8+p.id):0);
      if(this.options.labels||p.id===selected) {
        this.round(c,x-u*.44,y-u*1.15,u*.88,u*.4,5,'#ffffffee');
        this.text(c,`#${p.id}`,x,y-u*.86,Math.max(10,u*.25),'#34556d','center');
      }
      if(p.id%4===0)this.cart(c,x+u*.52,y+u*.1,u*.65,0);
      else if(!p.shopping||p.moving){this.round(c,x+u*.22,y-u*.23,u*.33,u*.24,3,'#bd9962');}
      if(snapshot.status[p.id]==='service')this.text(c,'€',x+u*.44,y-u*.55,Math.max(13,u*.4),'#27876f');
      if(snapshot.status[p.id]==='abandoned')this.text(c,'×',x+u*.4,y-u*.55,Math.max(14,u*.45),'#b64d69');
      c.restore();
    });
    if(drag?.kind==='person') {
      c.save();c.globalAlpha=.85;
      this.person(c,drag.point.x*ux,drag.point.y*uy,u*.14,drag.id,false,'#467dba',false);
      c.restore();
    }
    c.restore();
    this.round(c,w-205,14,189,34,8,'#ffffffed');
    this.text(c,`${RF.minutes(time)} / ${snapshot.waiting} en file`,w-110,36,13,'#375f73','center');
  }
  cart(c,x,y,u,angle=0,empty=false) {
    c.save();c.translate(x,y);c.rotate(angle);c.strokeStyle='#6c8580';c.lineWidth=Math.max(1,u*.07);
    c.fillStyle='#d8e2d480';c.beginPath();c.roundRect(-u*.33,-u*.5,u*.68,u*.75,u*.06);c.fill();c.stroke();
    for(let i=0;i<3;i++){c.beginPath();c.moveTo(-u*.3,(-.35+i*.18)*u);c.lineTo(u*.3,(-.35+i*.18)*u);c.stroke();}
    c.beginPath();c.moveTo(-u*.32,u*.25);c.lineTo(-u*.45,u*.48);c.lineTo(u*.28,u*.48);c.stroke();
    c.fillStyle='#506b66';for(const wx of [-.23,.23]){c.beginPath();c.arc(wx*u,u*.33,u*.07,0,Math.PI*2);c.fill();}
    if(!empty){c.fillStyle='#b6bd78';c.fillRect(-u*.2,-u*.2,u*.2,u*.25);c.fillStyle='#c59474';c.fillRect(u*.04,-u*.32,u*.18,u*.3);}
    c.restore();
  }
  person(c,x,y,pixel,id,cashier,shirt,walk) {
    const skin=['#ecc49b','#bb8d69','#79583f'][id%3],hair=['#594633','#2d3438','#c4a06b'][id%3];
    // Petit personnage arrondi, ombre, orientation et jambes alternées.
    this.round(c,x-pixel*1.45,y-pixel*1.1+walk*pixel*.25,pixel*1.15,pixel*2.0,pixel*.25,'#384e5c');
    this.round(c,x+pixel*.3,y-pixel*1.1-walk*pixel*.25,pixel*1.15,pixel*2.0,pixel*.25,'#384e5c');
    this.round(c,x-pixel*2.2,y-pixel*4.9,pixel*4.4,pixel*4.4,pixel*1.1,shirt);
    this.round(c,x-pixel*2.8,y-pixel*4,pixel*.9,pixel*2.7,pixel*.35,skin);
    this.round(c,x+pixel*1.9,y-pixel*4,pixel*.9,pixel*2.7,pixel*.35,skin);
    this.round(c,x-pixel*1.65,y-pixel*7.5,pixel*3.3,pixel*3.8,pixel*1.1,skin);
    this.round(c,x-pixel*1.75,y-pixel*7.8,pixel*3.5,pixel*1.65,pixel*.7,hair);
    if(cashier){c.fillStyle='#fff8e4';c.fillRect(x-pixel*.8,y-pixel*4.3,pixel*1.6,pixel*1.8);}
  }
};
