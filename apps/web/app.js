const $ = (id) => document.getElementById(id);
let selected = null;
let poll = null;
function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {'Content-Type':'application/json','X-Team-Token':$('token').value,...options.headers}});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}
function table(headers, rows) { const t=node('table'); const head=node('tr'); headers.forEach(h=>head.append(node('th',h))); t.append(head); rows.forEach(row=>{const tr=node('tr');row.forEach(cell=>tr.append(node('td',String(cell ?? 'Not available'))));t.append(tr);});return t; }
function fmt(value) { return value == null ? 'Not available' : Number(value).toFixed(3); }
async function refresh() {
  try { const runs=await api('/api/runs');$('runs').replaceChildren();runs.forEach(run=>{const b=node('button',`${run.id.slice(0,8)} / ${run.state}`);b.onclick=()=>show(run.id);$('runs').append(b);}); } catch(e){$('message').textContent=e.message;}
}
async function show(id) {
  clearTimeout(poll); selected=id;
  try {
    const run=await api(`/api/runs/${id}`); const root=$('result');root.replaceChildren(node('h2',`Experiment ${id.slice(0,8)}`));
    if(run.state!=='completed'){root.append(node('p',run.error || `Status: ${run.state}. The worker processes one experiment at a time.`));if(['pending','running'].includes(run.state))poll=setTimeout(()=>show(id),1200);return;}
    $('message').textContent='Experiment completed.';const r=run.report;root.append(node('span',r.mode==='demo'?'SIMULATED DEMO / NOT RELEASE EVIDENCE':'LIVE MODEL EVALUATION','badge'));
    root.append(node('p',r.dataset_provenance,'muted'));
    root.append(node('h3',r.gate.passed?'Release criteria passed':'Release approval withheld'));
    r.gate.reasons.forEach(reason=>root.append(node('p',reason,'muted')));
    const stats=node('div',undefined,'stats');[['Calls',r.metrics.calls],['Cost USD',fmt(r.metrics.cost_usd)],['Call p50 sec',fmt(r.metrics.latency_p50)],['Call p99 sec',fmt(r.metrics.latency_p99)]].forEach(([label,value])=>{const d=node('div',undefined,'stat');d.append(node('strong',String(value)),node('span',label));stats.append(d);});root.append(stats);
    root.append(node('h3','Answer comparison'),table(['Judge','System','Mean / 4','95% bootstrap interval','Consistent wins'],r.leaderboard.map(x=>[x.judge,x.system,x.mean_score,x.score_interval.join(' to '),x.wins])));
    root.append(node('h3','Judge quality'),table(['Judge','Human labels','Agreement','False acceptance','Order consistency'],r.calibration.map(x=>[x.judge,x.human_labels,fmt(x.agreement),fmt(x.false_acceptance),fmt(x.order_consistency)])));
    root.append(node('p','Confidence intervals resample scenarios. Demo fixture labels are not human ground truth.','muted'));
    root.append(node('h3','Inspect examples'));
    const filter=node('label','Filter examples');const toggle=document.createElement('input');toggle.type='checkbox';filter.append(toggle,node('span','Only disagreements'));root.append(filter);
    const examples=node('div');root.append(examples);
    function draw(){examples.replaceChildren();r.rows.filter(row=>!toggle.checked||r.disagreements.includes(row.case_id)).forEach(row=>{
      const details=node('details',undefined,'case');details.append(node('summary',`${row.case_id} / ${row.judge} / ${row.preference}${row.order_consistent?'':' / ORDER DISAGREEMENT'}`));details.append(node('p',row.question));
      row.evidence.forEach(e=>{details.append(node('pre',e.text));const a=node('a','Official source');if(/^https:\/\//.test(e.url)){a.href=e.url;a.target='_blank';a.rel='noopener noreferrer';}details.append(a);});
      const answers=node('div',undefined,'answers');Object.entries(row.answers).forEach(([name,text])=>{const d=node('div');d.append(node('h3',`Answer ${name}`),node('pre',text),node('p',`${row.points[name].verdict} / ${JSON.stringify(row.points[name].scores)}`),node('p',row.points[name].reason));answers.append(d);});details.append(answers,node('p',`Forward: ${row.forward.preference}. Reversed: ${row.reverse.preference}.`));
      const form=node('form',undefined,'review');const reviewer=document.createElement('input');reviewer.placeholder='Your GitHub handle';reviewer.required=true;const labels={};['A','B'].forEach(name=>{const label=node('label',`Human verdict for ${name}`);const select=node('select');['accept','reject'].forEach(v=>{const o=node('option',v);o.value=v;select.append(o);});labels[name]=select;label.append(select);form.append(label);});const pref=node('select');['A','B','tie','insufficient'].forEach(v=>{const o=node('option',v);o.value=v;pref.append(o);});const rationale=node('textarea');rationale.placeholder='Reason and policy evidence';rationale.required=true;const save=node('button','Record independent review');const feedback=node('p');form.prepend(reviewer);form.append(node('label','Pairwise preference'),pref,rationale,save,feedback);form.onsubmit=async event=>{event.preventDefault();try{await api(`/api/runs/${id}/annotations`,{method:'POST',body:JSON.stringify({case_id:row.case_id,reviewer:reviewer.value,verdicts:{A:labels.A.value,B:labels.B.value},preference:pref.value,rationale:rationale.value})});feedback.textContent='Saved. Adjudicate independently before importing as gold labels.';}catch(e){feedback.textContent=e.message;}};details.append(form);examples.append(details);
    });} toggle.onchange=draw;draw();
    const download=node('a','Download full JSON report');download.href=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)],{type:'application/json'}));download.download=`supportjudge-${id}.json`;root.append(download);
    const versions=node('details');versions.append(node('summary','Pinned versions'),node('pre',JSON.stringify(r.versions,null,2)));root.append(versions);
    refresh();
  } catch(e){$('message').textContent=e.message;}
}
$('experiment').onsubmit=async event=>{event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{const result=await api('/api/runs',{method:'POST',body:JSON.stringify({dataset:$('dataset').value,mode:$('mode').value,answer_source:$('answers').value,split:$('split').value})});$('message').textContent='Experiment queued.';await refresh();await show(result.id);}catch(e){$('message').textContent=e.message;}finally{button.disabled=false;}};
$('refresh').onclick=refresh;
async function init(){try{const datasets=await api('/api/datasets');datasets.forEach(d=>{const option=node('option',`${d.name} / ${d.cases} cases`);option.value=d.name;$('dataset').append(option);});await refresh();}catch(e){$('message').textContent=e.message;}}
init();
