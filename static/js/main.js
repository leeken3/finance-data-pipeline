// Shared, page-independent browser setup.
document.addEventListener("DOMContentLoaded", () => {
  const dropzone = document.querySelector("#csv-dropzone");
  const fileInput = document.querySelector("#statement-file");
  const title = document.querySelector("#dropzone-title");
  const detail = document.querySelector("#dropzone-detail");

  if (!dropzone || !fileInput) return;

  function showFile(file) {
    if (!file) return;
    title.textContent = file.name;
    detail.textContent = `${(file.size / 1024).toFixed(1)} KB — ready to import`;
  }

  fileInput.addEventListener("change", () => showFile(fileInput.files[0]));

  for (const eventName of ["dragenter", "dragover"]) {
    dropzone.addEventListener(eventName, event => {
      event.preventDefault();
      dropzone.classList.add("dragging");
    });
  }

  for (const eventName of ["dragleave", "drop"]) {
    dropzone.addEventListener(eventName, event => {
      event.preventDefault();
      dropzone.classList.remove("dragging");
    });
  }

  dropzone.addEventListener("drop", event => {
    const file = [...(event.dataTransfer?.files || [])].find(item =>
      item.name.toLowerCase().endsWith(".csv") || item.type === "text/csv"
    );
    if (!file) {
      title.textContent = "Please drop a CSV file";
      detail.textContent = "Supported format: .csv";
      return;
    }
    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;
    showFile(file);
  });
});
