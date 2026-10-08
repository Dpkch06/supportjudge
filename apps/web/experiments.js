async function refresh(){
  const status=document.getElementById('status'),list=document.getElementById('saved-list');
  status.textContent='Loading experiments...';
  try{const response=await fetch('/api/experiments');if(!response.ok)throw Error('Unable to load experiments.');const runs=await response.json(),byId=new Map(runs.map(r=>[r.id,r]));list.replaceChildren();
    runs.forEach(run=>{const a=document.createElement('a');a.className='saved-experiment';a.href=`/experiments/${run.id}`;const info=document.createElement('div'),title=document.createElement('strong'),description=document.createElement('p'),state=document.createElement('span');title.textContent=`Experiment ${run.number}`;description.textContent=run.baseline_id?`Rubric version of Experiment ${byId.get(run.baseline_id)?.number??''}: ${run.rubric_name}`:new Date(run.created).toLocaleString();state.className='badge';state.textContent=run.state;info.append(title,description);a.append(info,state);list.append(a);});status.textContent=runs.length?'':'No experiments yet. Start one from New experiment.';
  }catch(e){status.textContent=e.message;}
}
document.getElementById('refresh').onclick=refresh;refresh();
