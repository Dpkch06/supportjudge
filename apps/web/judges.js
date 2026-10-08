const $=id=>document.getElementById(id);
function node(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;}
async function api(path){const r=await fetch(path),data=await r.json();if(!r.ok)throw Error(data.detail||'Request failed');return data;}
function table(headers,rows){const t=node('table'),h=node('tr');headers.forEach(x=>h.append(node('th',x)));t.append(h);rows.forEach(row=>{const tr=node('tr');row.forEach(x=>tr.append(node('td',String(x))));t.append(tr);});return t;}
const pct=x=>`${(100*x).toFixed(1)}%`;
function compareRows(rows){
  const judges=[...new Set(rows.map(r=>r.judge))], cases=new Map(), pairs=[];
  rows.forEach(r=>{if(!cases.has(r.case_id))cases.set(r.case_id,[]);cases.get(r.case_id).push(r);});
  for(let i=0;i<judges.length;i++)for(let j=i+1;j<judges.length;j++){
    let count=0,preferences=0,verdicts=0,gap=0,scores=0;
    cases.forEach(group=>{const a=group.find(r=>r.judge===judges[i]),b=group.find(r=>r.judge===judges[j]);if(!a||!b)return;
      if(['A','B'].some(s=>a.answers[s]!==b.answers[s])||JSON.stringify(a.evidence)!==JSON.stringify(b.evidence))throw Error('These judges evaluated different answers or evidence.');
      count++;preferences+=a.preference===b.preference;
      ['A','B'].forEach(s=>{verdicts+=a.points[s].verdict===b.points[s].verdict;Object.keys(a.points[s].scores).forEach(d=>{gap+=Math.abs(a.points[s].scores[d]-b.points[s].scores[d]);scores++;});});
    });
    if(count)pairs.push([judges[i],judges[j],count,pct(preferences/count),pct(verdicts/(count*2)),(gap/scores).toFixed(2)]);
  }
  return {pairs,cases};
}
async function compare(){
  const id=$('experiment-choice').value;if(!id)return;
  const experimentName=$('experiment-choice').selectedOptions[0].textContent;
  $('compare').disabled=true;$('status').textContent='Preparing judge comparison...';$('report').hidden=true;
  try{
    const run=await api(`/api/runs/${id}`);if(run.state!=='completed')throw Error('Select a completed experiment.');
    const r=run.report,{pairs,cases}=compareRows(r.rows),root=$('report');
    root.replaceChildren(node('h2',experimentName));
    const link=node('a','Open saved experiment and rubric');link.href=`/experiments/${id}`;root.append(link);
    root.append(node('h3','Scores by judge'),table(['Judge','Answer','Mean / 4','95% interval','Consistent wins'],r.leaderboard.map(x=>[x.judge,x.system,x.mean_score,x.score_interval.join(' to '),x.wins])));
    root.append(node('h3','Agreement between judges'),table(['Judge 1','Judge 2','Matched questions','Preference agreement','Verdict agreement','Mean absolute score gap / 4'],pairs));
    root.append(node('h3','Position sensitivity'),table(['Judge','Consistent after swapping answers'],r.calibration.map(x=>[x.judge,pct(x.order_consistency)])));
    const disagrees=group=>new Set(group.map(x=>x.preference)).size>1||['A','B'].some(a=>new Set(group.map(x=>x.points[a].verdict)).size>1)||group.some(x=>!x.order_consistent);
    root.append(node('p',`${[...cases.values()].filter(disagrees).length} of ${cases.size} questions have differing verdicts, preferences, or an order-sensitive result.`));
    const label=node('label','Only disagreements'),filter=node('input');filter.type='checkbox';label.append(filter);root.append(label);const examples=node('div');root.append(examples);
    function draw(){
      examples.replaceChildren();cases.forEach(group=>{if(filter.checked&&!disagrees(group))return;const r=group[0],box=node('details');box.className='case';box.append(node('summary',r.question));
        const answers=node('div');answers.className='answers';Object.entries(r.answers).forEach(([a,text])=>{const div=node('div');div.append(node('h3',`Answer ${a}`),node('pre',text));answers.append(div);});box.append(answers);
        r.evidence.forEach(e=>{box.append(node('pre',e.text));if(e.url.startsWith('https://')){const link=node('a','Policy source');link.href=e.url;link.target='_blank';link.rel='noopener noreferrer';box.append(link);}});
        const judgments=node('div');judgments.className='answers';group.forEach(j=>{const div=node('div');div.append(node('h3',j.judge),node('p',`Preference: ${j.preference}. Order ${j.order_consistent?'consistent':'inconsistent'}.`),node('p',j.forward.reason));['A','B'].forEach(a=>div.append(node('h3',`Answer ${a}: ${j.points[a].verdict}`),table(['Dimension','Score'],Object.entries(j.points[a].scores)),node('p',j.points[a].reason)));judgments.append(div);});box.append(judgments);examples.append(box);
      });if(!examples.children.length)examples.append(node('p','No disagreements in this experiment.'));
    }
    filter.onchange=draw;draw();root.hidden=false;$('status').textContent='Comparison ready.';
    const url=new URL(location.href);url.searchParams.set('experiment',id);history.replaceState({},'',url);
  }catch(e){$('status').textContent=e.message;}finally{$('compare').disabled=false;}
}
$('judge-form').onsubmit=e=>{e.preventDefault();compare();};
$('experiment-choice').onchange=compare;
async function init(){try{const runs=(await api('/api/experiments')).filter(r=>r.state==='completed');runs.forEach(r=>{const o=node('option',`Experiment ${r.number}`);o.value=r.id;$('experiment-choice').append(o);});if(!runs.length){$('status').textContent='Complete an experiment to compare its judges.';return;}$('compare').disabled=false;const chosen=new URL(location.href).searchParams.get('experiment');if(chosen&&runs.some(r=>r.id===chosen)){$('experiment-choice').value=chosen;}compare();}catch(e){$('status').textContent=e.message;}}
init();
