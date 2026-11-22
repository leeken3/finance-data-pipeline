document.addEventListener('DOMContentLoaded',()=>{
  const checks=[...document.querySelectorAll('.transaction-checkbox')];
  const header=document.querySelector('#header-check');
  const deleteButton=document.querySelector('#delete-selected');
  const form=document.querySelector('#history-delete-form');
  function syncDeleteButton(){if(deleteButton)deleteButton.disabled=!checks.some(check=>check.checked)}
  checks.forEach(check=>check.addEventListener('change',()=>{
    syncDeleteButton();
    if(header)header.checked=checks.length>0&&checks.every(item=>item.checked);
  }));
  if(header)header.addEventListener('change',()=>{checks.forEach(check=>check.checked=header.checked);syncDeleteButton()});
  if(form)form.addEventListener('submit',event=>{if(!checks.some(check=>check.checked)||!confirm('Delete the selected transactions?'))event.preventDefault()});
  const search=document.querySelector('.search-field input[type="search"]');
  if(search){
    search.addEventListener('search',()=>{if(search.value==='')search.form.submit()});
    search.addEventListener('input',()=>{if(search.value==='')search.form.submit()});
  }
  syncDeleteButton();
});
