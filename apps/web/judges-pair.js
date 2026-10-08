const $=id=>document.getElementById(id);
let experiments=new Map(),requestSequence=0;
function node(tag,text){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el;}
async function api(path){const response=await fetch(path),data=await response.json();if(!response.ok)throw Error(data.detail||'Unable to load comparison');return data;}
function table(headers,rows){const el=node('table'),head=node('tr');headers.forEach(h=>head.append(node('th',h)));el.append(head);rows.forEach(row=>{const tr=node('tr');row.forEach(v=>tr.append(node('td',String(v))));el.append(tr);});return el;}
function link(label,url){const a=node('a',label);a.href=url;return a;}
async function show(){
  const id=$('pair-choice').value,sequence=++requestSequence;if(!id)return;
  $('show-pair').disabled=true;$('pair-report').hidden=true;$('status').textContent='Loading saved versions...';
  try{
    const version=experiments.get(id),baseline=experiments.get(version.baseline_id);
    const result=await api(`/api/runs/${id}/rubric-result`);
    if(sequence!==requestSequence)return;
    if(result.comparison.baseline_id!==baseline.id)throw Error('The selected versions are not related.');
    const before=`Experiment ${baseline.number}`,after=`Experiment ${version.number}`,root=$('pair-report');
    const intro=node('section');intro.className='panel';intro.append(node('h2',`${before} vs ${after}`),node('p',`${before} is the original. ${after} is its rubric-change version: ${result.comparison.name}.`));
    intro.append(link(`Open ${before}`,`/experiments/${baseline.id}`),node('span',' | '),link(`Open ${after}`,`/experiments/${id}`));
    intro.append(node('h3','What changed in the rubric'),table(['Dimension','Score',before,after],result.rubric_changes.map(r=>[r.dimension,r.score,r.before,r.after])));
    root.replaceChildren(intro);
    const judges=[...new Set(result.scores.map(s=>s.judge))];
    judges.forEach(judge=>{
      const section=node('section');section.className='panel judge-version-card';section.style.marginTop='18px';
      section.append(node('h2',judge),node('p',`${judge} in ${before} compared with ${judge} in ${after}.`));
      const scores=result.scores.filter(s=>s.judge===judge),examples=result.examples.filter(e=>e.judge===judge);
      section.append(node('p',`${scores.filter(s=>s.delta!==0).length} average dimension scores changed; ${examples.filter(e=>e.preference_changed).length} question preferences changed.`));
      section.append(table(['Answer','Dimension',before,after,'Change'],scores.map(s=>[s.answer,s.dimension,s.before.toFixed(2),s.after.toFixed(2),`${s.delta>0?'+':''}${s.delta.toFixed(2)}`])));
      examples.forEach(e=>{
        const detail=node('details');detail.className='case';detail.append(node('summary',e.question),table(['Measure',before,after],[['Preference',e.before.preference,e.after.preference],['Order consistent',e.before.order_consistent,e.after.order_consistent]]));
        ['A','B'].forEach(answer=>{detail.append(node('h3',`Answer ${answer}`),node('pre',e.before.answers[answer]),table(['Verdict',before,after],[[answer,e.before.points[answer].verdict,e.after.points[answer].verdict]]));const reasons=node('div');reasons.className='answers';for(const [name,row] of [[before,e.before],[after,e.after]]){const col=node('div');col.append(node('h3',name),node('p',row.points[answer].reason));reasons.append(col);}detail.append(reasons);});
        section.append(detail);
      });root.append(section);
    });
    root.append(node('p',result.note));root.hidden=false;$('status').textContent=`Rubric comparison ready: ${before} vs ${after}. No new model calls.`;
    const url=new URL(location.href);url.searchParams.set('experiment',id);history.replaceState({},'',url);
  }catch(e){if(sequence===requestSequence)$('status').textContent=e.message;}finally{if(sequence===requestSequence)$('show-pair').disabled=false;}
}
$('pair-form').onsubmit=e=>{e.preventDefault();show();};$('pair-choice').onchange=show;
async function init(){try{
  const all=await api('/api/experiments');experiments=new Map(all.map(r=>[r.id,r]));
  const versions=all.filter(r=>r.state==='completed'&&r.baseline_id&&experiments.get(r.baseline_id)?.state==='completed');
  versions.forEach(r=>{const o=node('option',`Experiment ${experiments.get(r.baseline_id).number} vs Experiment ${r.number} - ${r.rubric_name}`);o.value=r.id;$('pair-choice').append(o);});
  if(!versions.length){$('status').textContent='No completed rubric versions yet. Open an experiment and run an edited rubric to compare rubric versions.';return;}
  const requested=new URL(location.href).searchParams.get('experiment');
  if(requested){if(!versions.some(r=>r.id===requested)){$('status').textContent='This experiment has no completed parent comparison. Choose an available pair.';$('show-pair').disabled=false;return;}$('pair-choice').value=requested;}
  await show();
}catch(e){$('status').textContent=e.message;}}
init();
