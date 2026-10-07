const $ = (id) => document.getElementById(id);
function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {'Content-Type':'application/json',...options.headers}});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}
function table(headers, rows) { const t=node('table'); const head=node('tr'); headers.forEach(h=>head.append(node('th',h))); t.append(head); rows.forEach(row=>{const tr=node('tr');row.forEach(cell=>tr.append(node('td',String(cell ?? 'Not available'))));t.append(tr);});return t; }
function fmt(value) { return value == null ? 'Not available' : Number(value).toFixed(3); }
const experimentNumbers = new Map();
async function refresh() {
  try {
    const runs=await api('/api/experiments');
    $('runs').replaceChildren();
    runs.forEach(run=>{
      experimentNumbers.set(run.id,run.number);
      const button=node('button',`Experiment ${run.number}`);
      button.title=run.state;
      button.onclick=()=>{window.location.href=`/experiments/${run.id}`;};
      $('runs').append(button);
    });
  } catch(e){$('message').textContent=e.message;}
}
$('refresh').onclick=refresh;
$('experiment').onsubmit=async event=>{event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{const result=await api('/api/runs',{method:'POST',body:JSON.stringify({dataset:$('dataset').value,mode:'live',answer_source:'generate',split:$('split').value,generator_models:[$('generator-a').value,$('generator-b').value],judge_selection:$('judge-selection').value,judge_models:$('judge-selection').value==='manual'?[$('judge-a').value,$('judge-b').value]:null})});$('message').textContent=`Experiment queued. Judges: ${result.judges.join(' and ')}.`;window.location.href=`/experiments/${result.id}`;}catch(e){$('message').textContent=e.message;}finally{updateModelChoices();}};
async function init(){
  try {
    const datasets=await api('/api/datasets');
    datasets.forEach(d=>{const option=node('option',d.name);option.value=d.name;$('dataset').append(option);});
    const roles=await api('/api/model-roles');
    const models=await api('/api/models');
    ['generator-a','generator-b','judge-a','judge-b'].forEach(id=>{
      models.filter(m=>id.startsWith('generator')||m.judge_supported).forEach(m=>{const option=node('option',m.name);option.value=m.id;$(id).append(option);});
    });
    $('generator-a').value=roles.generators[0].model;
    $('generator-b').value=roles.generators[1].model;
    $('judge-a').value='anthropic/claude-haiku-4.5';
    $('judge-b').value='deepseek/deepseek-chat-v3.1';
    ['generator-a','generator-b','judge-a','judge-b','judge-selection'].forEach(id=>$(id).onchange=updateModelChoices);
    updateModelChoices();
    await refresh();
  }catch(e){$('message').textContent=e.message;}
}
function updateModelChoices(){
  const manual=$('judge-selection').value==='manual';
  $('judge-a-label').hidden=!manual;$('judge-b-label').hidden=!manual;
  const generators=[$('generator-a').value,$('generator-b').value];
  ['judge-a','judge-b'].forEach(id=>Array.from($(id).options).forEach(o=>{o.disabled=generators.includes(o.value);}));
  const judges=[$('judge-a').value,$('judge-b').value];
  const invalid=new Set(generators).size<2 || generators.some(x=>!x) || (manual && (new Set(judges).size<2 || judges.some(x=>!x||generators.includes(x))));
  $('run-button').disabled=invalid;
  $('model-roles').replaceChildren(node('p',invalid?'Select distinct generators and two separate judges.':manual?'Both selected judges score both generated answers.':'Each experiment rotates to a different pair of judges from different model providers. The selected generators are excluded.'));
}
init();
