document.addEventListener('DOMContentLoaded',()=>{
  const toggle=document.querySelector('#calendar-toggle');
  const menu=document.querySelector('#calendar-menu');
  if(!toggle||!menu)return;
  toggle.addEventListener('click',()=>menu.classList.toggle('open'));
  document.addEventListener('click',event=>{if(!event.target.closest('.period-picker'))menu.classList.remove('open')});
  document.querySelectorAll('[data-year-step]').forEach(button=>button.addEventListener('click',()=>{
    const input=document.querySelector('#calendar-year');
    const title=document.querySelector('#calendar-title');
    const step=Number(button.dataset.yearStep);
    const limit=Number(button.dataset.yearLimit||input.value);
    const next=step<0?Math.max(2000,Number(input.value)+step):Math.min(limit,Number(input.value)+step);
    input.value=String(next);title.textContent=String(next);
  }));
});
