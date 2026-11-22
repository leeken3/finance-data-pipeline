document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('.track i[data-width]').forEach(bar=>{bar.style.width=`${bar.dataset.width}%`});
  document.querySelectorAll('.column[data-height]').forEach(column=>{column.style.height=`${column.dataset.height}px`});
});
