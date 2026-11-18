// Interface de pilotage. Toute commande métier remonte à Python par le composant.
RF.mountStudio = (root,data,onAction) => {
  const find = role => root.querySelector(`[data-role="${role}"]`);
  const canvas=root.querySelector('canvas'),painter=new RF.StorePainter(canvas,data),replay=new RF.Replay(data);
  const controls=Object.fromEntries(['play','restart','next','speed','slider','clock','end','peak','help','fullscreen',
    'present','shopping','waiting','serving','served','abandoned','longest','start','start-play','start-peak','toast','viewport',
    'registers','open-next','client-inspector','events','heat','labels','trails','auto-pause','bookmark','bookmarks',
    'guide','guide-panel','guide-steps','guide-text','client-search','client-id','target-register','move-client','move-help','decisions','decision-count','capture','analysis','request-state','zoom-in','zoom-out','zoom-label','fit','help-panel','hover-hint'].map(k=>[k,find(k)]));
  root.classList.remove('pending','dragging');
  controls.registers.replaceChildren();
  controls['request-state'].textContent='';
  controls.toast.hidden=true;
  controls['hover-hint'].textContent='Cliquez une caisse. Déplacez un client en file vers une autre caisse.';
  for(const name of ['heat','labels','trails'])painter.options[name]=controls[name].checked;
  const storedKey=`retailflow_studio_${data.run_id}`;
  let saved={};try{saved=JSON.parse(sessionStorage.getItem(storedKey)||'{}');}catch{}
  const cursor=data.cursor || {};
  let time=RF.cursorTime(data,saved);
  const cursorToken=cursor.token||saved.cursorToken||null;
  if(saved.immersive)root.classList.add('immersive');
  painter.zoom=Math.max(1,Math.min(3,Number(saved.zoom)||1));
  if(saved.pan)painter.pan=saved.pan;
  painter.reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let playing=false,speed=Number(saved.speed)||5,selected=(cursor.token && cursor.token!==saved.cursorToken?cursor.followed:null)??saved.selected??null,hover=null;
  let snapshot=replay.at(time),lastStamp=null,raf=0,alive=true,dirty=true,lastHud=-1,lastSave=0,drag=null,pending=false;
  let pauseFired=false,toastTimer=0,inspectorSignature='',decisionSignature='';
  let sampleStart=performance.now(),drawCount=0,drawTotal=0,drawMax=0;
  let guideStep=Number(saved.guideStep)||0,guideOpen=Boolean(saved.guideOpen);
  function showGuide(){
    controls['guide-panel'].hidden=!guideOpen;controls.guide.setAttribute('aria-expanded',String(guideOpen));
    const descriptions=[
      'Situation : observez les paramètres, la graine et les caisses ouvertes. Les courses sont illustratives ; les événements aux caisses viennent du moteur.',
      'Congestion : la lecture est placée au pic. Identifiez les files et l’attente actuelle dans l’inspecteur.',
      'Décision : ouvrez une caisse fermée ou sélectionnez un client en file, puis choisissez une autre caisse. Python valide et recalcule le futur.',
      'Comparaison : sous l’atelier, ouvrez l’analyse Interventions. Comparez les bilans finaux au témoin, avec les mêmes arrivants et services prévus.',
      'Conclusion : commentez les écarts de moyenne, P90, abandons, service et ressources mobilisées. Plusieurs actions ont un effet combiné ; une graine ne suffit pas à généraliser.'
    ];
    controls['guide-text'].textContent=descriptions[guideStep];
    controls['guide-steps'].querySelectorAll('button').forEach((b,i)=>{b.setAttribute('aria-current',String(i===guideStep));b.onclick=()=>{guideStep=i;if(i===0){playing=false;seek(0);}if(i===1)peak();showGuide();save();};});
  }
  let bookmarks=Array.isArray(saved.bookmarks)?saved.bookmarks:[];
  controls.speed.value=String(speed);controls.end.textContent=RF.minutes(data.end_time);
  root.querySelector('.studio-head p').textContent=`${data.scenario} / ${data.customers.length} clients / ${data.initially_open} caisses initiales / graine ${data.seed}`;
  if(selected==null)controls['client-inspector'].innerHTML='<span class="eyebrow">INSPECTEUR CLIENT</span><h3>Chaque parcours compte.</h3><p>Cliquez sur un client pour le suivre. Glissez un client en file vers une autre caisse.</p>';
  const registerCards=data.layout.registers.map(r=>{
    const button=document.createElement('button');button.type='button';button.className='register-card';
    button.style.setProperty('--lane',RF.colours[r.id-1]);button.setAttribute('aria-label',`Ouvrir ou fermer la caisse ${r.id}`);
    const title=document.createElement('strong'),meta=document.createElement('div'),bar=document.createElement('div'),fill=document.createElement('i');
    meta.className='register-meta';bar.className='bar';bar.append(fill);button.append(title,meta,bar);
    button.onclick=()=>toggleRegister(r.id);controls.registers.append(button);
    return {id:r.id,button,title,meta,fill};
  });
  function save(){
    try{sessionStorage.setItem(storedKey,JSON.stringify({time,speed,selected,cursorToken,feedbackToken:saved.feedbackToken,guideStep,guideOpen,bookmarks,zoom:painter.zoom,pan:painter.pan,
      immersive:root.classList.contains('immersive')||document.fullscreenElement===root}));}catch{}
  }
  function toast(text) {controls.toast.textContent=text;controls.toast.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>controls.toast.hidden=true,4500);}
  function seek(next) {time=Math.max(0,Math.min(data.end_time,next));snapshot=replay.at(time);pauseFired=false;dirty=true;save();}
  function play(){if(pending)return;if(time>=data.end_time)seek(0);playing=!playing;dirty=true;}
  function request(action){
    if(pending)return;playing=false;pending=true;dirty=true;save();root.classList.add('pending');
    controls['request-state'].textContent='Calcul de votre intervention…';
    onAction({...action,time:Math.min(time,data.horizon),id:crypto.randomUUID(),run_id:data.run_id,
      followed:selected,revision:data.revision});
  }
  function toggleRegister(id){
    snapshot=replay.at(time);
    if(snapshot.open[id] && Object.values(snapshot.open).filter(Boolean).length===1){toast('La dernière caisse ouverte doit rester disponible.');return;}
    request({kind:'register',register_id:id,opened:!snapshot.open[id]});
  }
  function updateBookmarks(){
    controls.bookmarks.replaceChildren();const initial=document.createElement('option');initial.value='';initial.textContent='Mes repères';controls.bookmarks.append(initial);
    bookmarks.forEach((t,i)=>{const option=document.createElement('option');option.value=String(t);option.textContent=`Repère ${i+1} / ${RF.minutes(t)}`;controls.bookmarks.append(option);});
  }
  function peak(){playing=false;seek(data.peak_time||0);toast('Pic de clients en file dans ce scénario. Vous pouvez intervenir ici.');}
  function zoom(factor){painter.zoomBy(factor);dirty=true;controls['zoom-label'].textContent=`${Math.round(painter.zoom*100)} %`;}
  async function fullscreen(){
    if(document.fullscreenElement){await document.exitFullscreen();controls.fullscreen.textContent='⛶ Plein écran';save();return;}
    if(root.classList.contains('immersive')){root.classList.remove('immersive');controls.fullscreen.textContent='⛶ Plein écran';painter.resize();dirty=true;save();return;}
    try{await root.requestFullscreen();}catch{root.classList.add('immersive');}
    controls.fullscreen.textContent='⛶ Quitter le plein écran';painter.resize();dirty=true;save();
  }
  function hud(){
    const state=snapshot;
    const shoppers=(data.shopping_customers||[]).filter(c=>time>=c.start && time<c.end);
    controls.shopping.textContent=String(shoppers.length);
    controls.clock.textContent=RF.minutes(time);controls.slider.value=Math.round(time/data.end_time*10000);
    for(const [role,value] of [['present',state.present+shoppers.length],['waiting',state.waiting],['serving',state.inService],['served',state.served],['abandoned',state.abandoned],['longest',RF.minutes(state.longest)]])controls[role].textContent=String(value);
    controls.play.textContent=playing?'Ⅱ Pause':time===0?'▶ Démarrer':'▶ Reprendre';
    controls.start.hidden=time>0||playing;controls.play.disabled=pending;
    controls['open-next'].disabled=pending||Object.values(state.open).every(Boolean);
    registerCards.forEach(({id,button,title,meta,fill})=>{
      const open=state.open[id],cid=state.serving[id],queue=state.queues[id];
      title.textContent=`Caisse ${id} / ${open?(cid?'En service':'Disponible'):(cid?'Termine le client':'Fermée')}`;
      meta.textContent=`${queue.length} en file${cid?` / client ${cid}`:''}`;
      button.classList.toggle('closed',!open);button.disabled=pending;
      button.setAttribute('aria-pressed',String(open));
      const person=cid?data.people[cid]:null;
      fill.style.width=person?`${Math.max(0,Math.min(100,(time-person.service_start)/person.service_duration*100))}%`:'0%';
    });
    const signature=JSON.stringify([selected,state.status[selected],state.queues,time.toFixed(2)]);
    if(signature!==inspectorSignature){
      RF.inspect(controls['client-inspector'],data,selected,time,state);inspectorSignature=signature;
    }
    const destination=controls['target-register'];
    const previous=destination.value;
    const targetSignature=JSON.stringify([state.open,selected,state.queues]);
    if(destination.dataset.signature!==targetSignature){
    destination.dataset.signature=targetSignature;
    destination.replaceChildren();
    for(const r of data.layout.registers){
      const o=document.createElement('option');o.value=String(r.id);
      o.textContent=`Caisse ${r.id} / ${state.open[r.id]?'ouverte':'fermée'}`;
      o.disabled=!state.open[r.id]||state.queues[r.id].includes(selected);destination.append(o);
    }
    if([...destination.options].some(o=>o.value===previous&&!o.disabled))destination.value=previous;
    else destination.value=[...destination.options].find(o=>!o.disabled)?.value||'';
    }
    const movable=state.status[selected]==='waiting';
    controls['move-client'].disabled=pending||!movable||!destination.value;
    controls['move-help'].textContent=movable?'Arrivée et patience conservées. Validation par Python.':'Sélectionnez un client actuellement en file, hors service.';
    const nextDecisionSignature=JSON.stringify((data.decisions||[]).map(o=>o.time<=time));
    if(nextDecisionSignature!==decisionSignature){
      RF.renderDecisions(controls.decisions,data,time,t=>{playing=false;seek(t);});
      decisionSignature=nextDecisionSignature;
    }
    controls['decision-count'].textContent=`(${(data.decisions||[]).length})`;
    controls.events.replaceChildren();
    state.recent.forEach(e=>{
      const row=document.createElement('div');row.className='event';const t=document.createElement('b');t.textContent=RF.minutes(e.time);
      row.append(t,document.createTextNode(`${RF.eventLabels[e.type]}${e.customer_id!=null?` / #${e.customer_id}`:` / caisse ${e.register_id}`}`));controls.events.append(row);
    });
    if(!state.arrivals)controls.analysis.textContent=`${data.customers.length} clients sont attendus aux caisses ; ${shoppers.length} font déjà leurs courses. Lancez la lecture pour suivre les parcours.`;
    else if(state.overFive)controls.analysis.textContent=`${state.overFive} client${state.overFive>1?'s':''} attend${state.overFive>1?'ent':''} déjà plus de 5 min. La plus longue attente actuelle est de ${RF.minutes(state.longest)}. Testez une caisse supplémentaire ou une réaffectation.`;
    else if(state.waiting)controls.analysis.textContent=`${state.waiting} client${state.waiting>1?'s':''} en file et ${state.inService} en service. Aucun client actuellement en file ne dépasse 5 min. ${state.served} sont déjà servis, ${state.abandoned} ont abandonné.`;
    else controls.analysis.textContent=`Aucune file à cet instant. ${state.served} clients sont sortis après service et ${state.abandoned} ont abandonné. ${data.customers.length-state.arrivals} restent à arriver.`;
  }
  function frame(stamp){
    if(!alive)return;
    const dt=lastStamp==null?0:Math.min(.12,(stamp-lastStamp)/1000);lastStamp=stamp;
    if(playing&&!document.hidden){
      let next=Math.min(data.end_time,time+dt*speed*.5);
      const crossing=controls['auto-pause'].checked&&!pauseFired?RF.waitCrossing(data,time,next):null;
      if(crossing!==null){next=crossing;playing=false;pauseFired=true;toast('Pause automatique : une attente vient de dépasser 5 min.');}
      time=next;dirty=true;if(time>=data.end_time)playing=false;
    }
    if(dirty){snapshot=replay.at(time);
      if(controls['auto-pause'].checked && snapshot.longest>5 && !pauseFired && playing){playing=false;pauseFired=true;toast('Pause automatique : un client en file dépasse 5 minutes d’attente.');}
      const drawStart=performance.now();
      painter.draw(time,snapshot,selected,hover,drag);
      const elapsed=performance.now()-drawStart;
      drawCount++;drawTotal+=elapsed;drawMax=Math.max(drawMax,elapsed);
      if(stamp-sampleStart>=1000){
        root.dataset.renderStats=JSON.stringify({speed,playing,frames:drawCount,
          duration_ms:stamp-sampleStart,mean_draw_ms:drawTotal/drawCount,max_draw_ms:drawMax});
        sampleStart=stamp;drawCount=0;drawTotal=0;drawMax=0;
      }
      if(stamp-lastHud>100||!playing){hud();lastHud=stamp;}
      dirty=false;
    }
    if(playing && stamp-lastSave>1200){save();lastSave=stamp;}
    raf=requestAnimationFrame(frame);
  }
  controls.guide.onclick=()=>{guideOpen=!guideOpen;showGuide();save();};
  controls['client-search'].onsubmit=e=>{
    e.preventDefault();const id=Number(controls['client-id'].value);
    if(!data.people[id]){toast('Identifiant absent de ce scénario.');return;}
    selected=id;playing=false;dirty=true;save();toast(`Client #${id} sélectionné. Son état correspond à l'instant affiché.`);
  };
  controls['move-client'].onclick=()=>{if(snapshot.status[selected]==='waiting'&&controls['target-register'].value)request({kind:'move',customer_id:selected,register_id:Number(controls['target-register'].value)});};
  controls.play.onclick=play;controls['start-play'].onclick=play;
  controls.restart.onclick=()=>{playing=false;seek(0);};
  controls.next.onclick=()=>{playing=false;seek(data.events.find(e=>e.time>time)?.time??data.end_time);};
  controls.slider.oninput=()=>{playing=false;seek(Number(controls.slider.value)/10000*data.end_time);};
  controls.speed.onchange=()=>{speed=Number(controls.speed.value);save();};
  controls.peak.onclick=peak;controls['start-peak'].onclick=peak;
  controls['open-next'].onclick=()=>{const id=data.layout.registers.find(r=>!snapshot.open[r.id])?.id;if(id)toggleRegister(id);};
  controls.fullscreen.onclick=fullscreen;
  controls.help.onclick=()=>{controls['help-panel'].open=!controls['help-panel'].open;};
  for(const name of ['heat','labels','trails'])controls[name].onchange=()=>{painter.options[name]=controls[name].checked;dirty=true;};
  controls['zoom-in'].onclick=()=>zoom(1.2);controls['zoom-out'].onclick=()=>zoom(1/1.2);
  controls.fit.onclick=()=>{painter.resetCamera();controls['zoom-label'].textContent='100 %';dirty=true;};
  controls.bookmark.onclick=()=>{if(bookmarks.length>=12){toast('12 repères maximum.');return;}bookmarks.push(time);updateBookmarks();save();toast(`Instant ${RF.minutes(time)} ajouté aux repères.`);};
  controls.bookmarks.onchange=()=>{if(controls.bookmarks.value!==''){playing=false;seek(Number(controls.bookmarks.value));}};
  controls.capture.onclick=()=>{
    const a=document.createElement('a');a.download=`RetailFlow_${RF.minutes(time).replace(':','-')}.png`;a.href=canvas.toDataURL('image/png');a.click();
  };
  const point=e=>{const r=canvas.getBoundingClientRect();return painter.toWorld(e.clientX-r.left,e.clientY-r.top);};
  canvas.onpointerdown=e=>{
    if(pending)return;root.focus({preventScroll:true});const p=point(e),person=painter.personAt(p),rid=painter.registerAt(p);
    if(e.shiftKey || (!person&&!rid)){drag={kind:'pan',origin:{x:e.clientX,y:e.clientY},pan:{...painter.pan}};}
    else if(person){selected=person.id;drag={kind:'person',id:person.id,point:p,origin:{x:e.clientX,y:e.clientY},moved:false};playing=false;}
    else drag={kind:'register',id:rid,origin:{x:e.clientX,y:e.clientY}};
    canvas.setPointerCapture(e.pointerId);dirty=true;
  };
  canvas.onpointermove=e=>{
    const p=point(e);
    if(drag?.kind==='pan'){painter.pan={x:drag.pan.x+e.clientX-drag.origin.x,y:drag.pan.y+e.clientY-drag.origin.y};dirty=true;return;}
    if(drag?.kind==='person'){
      drag.point=p;drag.target=painter.laneAt(p);drag.moved ||= Math.hypot(e.clientX-drag.origin.x,e.clientY-drag.origin.y)>6;
      controls['hover-hint'].textContent=drag.target?`Déposer le client #${drag.id} à la caisse ${drag.target}`:'Choisissez la zone d’une caisse ouverte';dirty=true;return;
    }
    const person=painter.personAt(p),rid=painter.registerAt(p);const next=person?.id??null;
    if(next!==hover){hover=next;dirty=true;}
    canvas.style.cursor=person?'grab':rid?'pointer':'grab';
    if(person)controls['hover-hint'].textContent=`Client #${person.id} / ${snapshot.status[person.id]==='waiting'?'cliquez ou déplacez vers une autre file':'cliquez pour inspecter'}`;
    else if(rid)controls['hover-hint'].textContent=`Caisse ${rid} / cliquer pour ${snapshot.open[rid]?'fermer':'ouvrir'}`;
    else controls['hover-hint'].textContent='Glissez le fond pour déplacer la caméra. Molette pour zoomer.';
  };
  canvas.onpointerup=e=>{
    const active=drag;drag=null;dirty=true;if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);
    if(active?.kind==='register' && Math.hypot(e.clientX-active.origin.x,e.clientY-active.origin.y)<8)toggleRegister(active.id);
    if(active?.kind==='person' && active.moved){
      if(snapshot.status[active.id]!=='waiting'){toast('Seuls les clients encore en file peuvent être réaffectés. Les courses et le service se poursuivent normalement.');return;}
      const target=painter.laneAt(point(e));
      if(!target||!snapshot.open[target]){toast('Déposez le client dans la zone d’une caisse ouverte.');return;}
      if(snapshot.queues[target].includes(active.id)){toast('Ce client attend déjà dans cette file.');return;}
      request({kind:'move',customer_id:active.id,register_id:target});
    }
  };
  canvas.onpointercancel=()=>{drag=null;dirty=true;};
  canvas.onwheel=e=>{e.preventDefault();zoom(e.deltaY<0?1.08:1/1.08);};
  const onKey=e=>{
    if(['INPUT','SELECT','BUTTON','TEXTAREA','SUMMARY'].includes(e.target.tagName))return;
    if(e.code==='Space'){e.preventDefault();play();}
    if(e.code==='ArrowRight'||e.code==='ArrowLeft'){e.preventDefault();playing=false;seek(time+(e.code==='ArrowRight'?1:-1));}
    if(e.key==='+'||e.key==='=')zoom(1.2);if(e.key==='-')zoom(1/1.2);if(e.key.toLowerCase()==='f')fullscreen();
    if(e.key==='Escape'&&root.classList.contains('immersive')){root.classList.remove('immersive');painter.resize();dirty=true;}
  };
  root.addEventListener('keydown',onKey);
  const onVisibility=()=>{if(document.hidden){playing=false;dirty=true;save();}};
  document.addEventListener('visibilitychange',onVisibility);
  const resize=new ResizeObserver(()=>{painter.resize();dirty=true;});resize.observe(controls.viewport);
  painter.resize();controls['zoom-label'].textContent=`${Math.round(painter.zoom*100)} %`;
  if(root.classList.contains('immersive'))controls.fullscreen.textContent='⛶ Quitter le plein écran';
  showGuide();updateBookmarks();hud();raf=requestAnimationFrame(frame);
  if(data.feedback && cursor.token!==saved.feedbackToken){toast(data.feedback);saved.feedbackToken=cursor.token;}
  return ()=>{alive=false;cancelAnimationFrame(raf);clearTimeout(toastTimer);resize.disconnect();document.removeEventListener('visibilitychange',onVisibility);root.removeEventListener('keydown',onKey);save();};
};
