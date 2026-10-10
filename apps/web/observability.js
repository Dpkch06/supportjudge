(() => {
  const node=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el;};
  const toggle=node('button','Metrics');toggle.id='metrics-toggle';toggle.type='button';toggle.setAttribute('aria-controls','metrics-panel');toggle.setAttribute('aria-expanded','false');
  document.querySelector('body > header').append(toggle);
  const panel=node('aside');panel.id='metrics-panel';panel.hidden=true;panel.setAttribute('aria-label','Observability metrics');
  const heading=node('div');heading.className='metrics-heading';const title=node('h2','Observability');const close=node('button','Close');close.type='button';heading.append(title,close);
  const label=node('label','View');const scope=node('select');scope.id='metrics-scope';label.append(scope);
  const refresh=node('button','Refresh');refresh.type='button';refresh.className='secondary';
  const status=node('p');status.className='metrics-status';status.setAttribute('role','status');
  const content=node('div');panel.append(heading,label,refresh,status,content);document.body.append(panel);
  let opened=false,timer,controller,manual=false,renderedScope=null;
  const context=()=>document.querySelector('#experiment-choice, #pair-choice, #review-experiment')?.value || location.pathname.match(/^\/experiments\/([^/]+)$/)?.[1] || new URLSearchParams(location.search).get('experiment') || '';
  const fmt=(value,suffix='')=>value===null||value===undefined?'Not recorded':`${Number(value).toLocaleString(undefined,{maximumFractionDigits:2})}${suffix}`;
  const card=(root,label,value)=>{const box=node('div');box.className='metric-card';box.append(node('span',label),node('strong',value));root.append(box);};
  const grid=()=>{const el=node('div');el.className='metrics-grid';content.append(el);return el;};
  const note=text=>{const el=node('p',text);el.className='metrics-note';content.append(el);};
  async function json(path,signal){const response=await fetch(path,{signal});if(!response.ok)throw Error(`Could not load metrics (${response.status}).`);return response.json();}
  async function load(){
    if(!opened||document.hidden)return;
    clearTimeout(timer);controller?.abort();const request=new AbortController();controller=request;
    status.textContent='Updating…';
    try{
      const runs=await json('/api/experiments',request.signal);
      const desired=manual?scope.value:context();
      scope.replaceChildren();const overview=node('option','Overview');overview.value='';scope.append(overview);
      runs.forEach(run=>{const option=node('option',`Experiment ${run.number} · ${run.state}`);option.value=run.id;scope.append(option);});
      scope.value=runs.some(run=>run.id===desired)?desired:'';
      const selected=scope.value;
      const data=await json(selected?`/api/runs/${encodeURIComponent(selected)}`:'/api/observability',request.signal);
      if(request.signal.aborted)return;
      const expanded=renderedScope===selected?[...content.querySelectorAll('details')].map(el=>el.open):[];
      renderedScope=selected;
      content.replaceChildren();const cards=grid();
      if(!selected){
        card(cards,'Experiments',fmt(data.runs));
        for(const state of ['pending','running','completed','failed'])card(cards,state[0].toUpperCase()+state.slice(1),fmt(data.states[state]||0));
        card(cards,'Median runtime',fmt(data.run_p50_seconds,' s'));card(cards,'p99 runtime',fmt(data.run_p99_seconds,' s'));
        card(cards,'Reported tokens',fmt(data.reported_tokens));card(cards,'Judge disagreements',fmt(data.judge_disagreements));
        note('Latest 100 runs. Runtime, tokens and disagreements cover completed runs only. Median is the middle runtime; p99 is the runtime below which approximately 99% of completed runs fall.');
      }else{
        card(cards,'Status',data.state);
        const report=data.report;
        if(report){
          const traces=report.traces||[];
          card(cards,'Runtime',fmt(report.elapsed_seconds,' s'));card(cards,'Recorded calls',fmt(traces.length));
          card(cards,'Reported tokens',fmt(report.metrics?.tokens));card(cards,'Cache hits',fmt(traces.filter(t=>t.cache_hit).length));
          card(cards,'Judge disagreements',fmt(report.disagreements?.length));
          // A null charge is unknown, not a free model call.
          const cost=report.metrics?.cost_usd;card(cards,'Reported cost',cost==null?'Not recorded':`$${Number(cost).toFixed(6)}`);
          note('Saved measurements for this experiment. Cached calls reuse earlier output and report no new tokens or charge. Provider-reported cost may differ from final billing.');
          const details=node('details');details.append(node('summary',`Model-call traces (${traces.length})`));
          traces.forEach((trace,index)=>{const item=node('details');item.className='metric-trace';item.append(node('summary',`${index+1}. ${trace.model}${trace.cache_hit?' · cached':''}`));const values=node('dl');
            for(const [key,value] of [['Latency',fmt(trace.latency_seconds,' s')],['Tokens',fmt(trace.tokens)],['Reported cost',trace.cost_usd==null?'Not recorded':`$${Number(trace.cost_usd).toFixed(6)}`]])values.append(node('dt',key),node('dd',value));
            item.append(values);details.append(item);});content.append(details);
        }else{note(data.state==='failed'?'This experiment failed. Partial model-call usage was not saved in a completed report.':'Detailed usage and traces will appear when this experiment finishes.');if(data.error)note(data.error);}
        const link=node('a','Open experiment results');link.href=`/experiments/${encodeURIComponent(selected)}`;content.append(link);
      }
      content.querySelectorAll('details').forEach((el,index)=>{el.open=expanded[index]||false;});
      status.textContent=`Updated ${new Date().toLocaleTimeString()} · refreshes every 10 seconds`;
    }catch(error){if(error.name!=='AbortError')status.textContent=`${error.message} Displayed values may be out of date. Try Refresh.`;}
    finally{if(opened&&controller===request)timer=setTimeout(load,10000);}
  }
  function setOpen(value){opened=value;panel.hidden=!value;document.body.classList.toggle('metrics-open',value);toggle.setAttribute('aria-expanded',String(value));if(value){load();close.focus();}else{clearTimeout(timer);controller?.abort();toggle.focus();}}
  toggle.onclick=()=>setOpen(!opened);close.onclick=()=>setOpen(false);refresh.onclick=load;scope.onchange=()=>{manual=true;load();};
  document.addEventListener('change',event=>{if(event.target.matches('#experiment-choice, #pair-choice, #review-experiment')){manual=false;load();}});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&opened)setOpen(false);});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){clearTimeout(timer);controller?.abort();}else load();});
})();
