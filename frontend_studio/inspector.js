// Présentation du client et chronologie, limitée aux événements connus à l'instant T.
RF.inspect = (container,data,id,time,state) => {
  container.replaceChildren();
  const add=(tag,text,className='')=>{const e=document.createElement(tag);e.textContent=text;e.className=className;container.append(e);return e;};
  add('span','INSPECTEUR CLIENT','eyebrow');
  if(id==null){add('h3','Choisissez un client');add('p','Cliquez sur un personnage ou recherchez son numéro. Une réaffectation est aussi possible avec les commandes ci-dessous.');return;}
  const p=RF.clientAt(data,id,time,state),status=state.status[id];
  const shopping=(data.shopping_customers||[]).find(c=>c.id===id && time>=c.start && time<c.end);
  add('h3',`Client #${id}`);
  const facts=[['Situation',({waiting:'En file',service:'En service',served:'Servi et sorti',abandoned:'Abandon'})[status]||(shopping?'Courses illustratives':'Pas encore aux caisses')],
    ['Arrivée aux caisses',p.arrival===null?'Non observée':RF.minutes(p.arrival)],
    ['Caisse',p.register===null?'Non observée':String(p.register)],
    ['Position en file',p.position===null?'Sans objet':String(p.position)],
    ['Changements de file',String(p.switches)],['Attente cumulée',RF.minutes(p.wait)],
    ['Début du service',p.start===null?'Non observé':RF.minutes(p.start)],
    ['Service écoulé',p.start===null?'Non observé':RF.minutes((p.end??time)-p.start)],
    ['Sortie ou abandon',p.end===null?'Non observé':RF.minutes(p.end)]];
  for(const [label,value] of facts){const row=add('div','','fact'),left=document.createElement('span'),right=document.createElement('b');left.textContent=label;right.textContent=value;row.append(left,right);}
  if(shopping || p.arrival!==null)add('p','Rayons → allée principale → caisses. Parcours de courses illustratif, sans effet sur les calculs.','route-note');
  const list=add('ol','','client-timeline');list.setAttribute('aria-label','Événements observés du client');
  for(const e of p.events){const li=document.createElement('li');li.textContent=`${RF.minutes(e.time)} : ${RF.eventLabels[e.type]}${e.target_register_id?` vers caisse ${e.target_register_id}`:e.register_id?` caisse ${e.register_id}`:''}`;list.append(li);}
  if(!p.events.length)add('p','Aucun événement moteur à cet instant.');
};
RF.renderDecisions=(container,data,time,seek)=>{
  container.replaceChildren();
  const rows=data.decisions||[];
  if(!rows.length){container.textContent='Aucune décision. Cliquez sur une caisse pour commencer.';return;}
  for(const o of rows){const a=o.action,row=document.createElement('button');row.className='decision-row';
    row.textContent=`${RF.minutes(o.time)} : ${a.kind==='move'?`client #${a.customer_id} →`:(a.opened?'ouvrir':'fermer')} caisse ${a.register_id} / ${o.time>time?'à venir':o.applied?'appliquée':'non appliquée'}`;
    const state=document.createElement('span');state.className='decision-state';
    state.textContent=o.time>time?'Décision programmée, résultat visible à cet instant.':`Avant : ${o.before}. Après : ${o.after}. ${o.reason}.`;
    row.append(state);row.onclick=()=>seek(o.time);container.append(row);
  }
};
