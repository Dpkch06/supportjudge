(() => {
  const mobile=matchMedia('(max-width: 760px)');
  const sidebar=document.createElement('aside');sidebar.id='app-sidebar';sidebar.setAttribute('aria-label','Sidebar');
  const toggle=document.createElement('button');toggle.id='sidebar-toggle';toggle.type='button';toggle.setAttribute('aria-controls','sidebar-navigation');
  toggle.innerHTML='<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/></svg>';
  const nav=document.createElement('nav');nav.id='sidebar-navigation';nav.setAttribute('aria-label','Main navigation');
  const links=[['/','New experiment'],['/experiments','Experiments'],['/judge-comparison','Compare judges'],['/judges-pair','Compare rubric versions'],['/docs','API reference']];
  links.forEach(([href,label])=>{const a=document.createElement('a');a.href=href;a.textContent=label;if(location.pathname===href||(href==='/experiments'&&location.pathname.startsWith('/experiments/')))a.setAttribute('aria-current','page');nav.append(a);});
  sidebar.append(toggle,nav);document.body.prepend(sidebar);
  const backdrop=document.createElement('button');backdrop.id='sidebar-backdrop';backdrop.setAttribute('aria-label','Close sidebar');backdrop.tabIndex=-1;document.body.append(backdrop);
  let stored=true;try{stored=localStorage.getItem('supportjudge-sidebar')!=='closed';}catch{}
  let open=mobile.matches?false:stored;
  function render(){document.body.classList.toggle('sidebar-open',open);toggle.setAttribute('aria-expanded',String(open));toggle.setAttribute('aria-label',open?'Close sidebar':'Open sidebar');toggle.title=open?'Close sidebar':'Open sidebar';nav.hidden=!open;backdrop.hidden=!(open&&mobile.matches);}
  function setOpen(value){open=value;if(!mobile.matches){stored=value;try{localStorage.setItem('supportjudge-sidebar',value?'open':'closed');}catch{}}render();}
  toggle.onclick=()=>setOpen(!open);backdrop.onclick=()=>{setOpen(false);toggle.focus();};
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&open){setOpen(false);toggle.focus();}});
  mobile.addEventListener('change',()=>{open=mobile.matches?false:stored;render();});
  render();
})();
