document.addEventListener("DOMContentLoaded", () => {
  const amountInput = document.querySelector("#transaction-amount");
  const splitInput = document.querySelector("#transaction-split");

  if (!amountInput || !splitInput) return;

  let originalAmount = Number(amountInput.value);

  amountInput.addEventListener("input", () => {
    originalAmount = Number(amountInput.value);
  });

  function applySplit() {
    const split = Number(splitInput.value);

    if (!Number.isFinite(split) || split < 1) {
      amountInput.value = originalAmount.toFixed(2);
      return;
    }

    const splitAmount = originalAmount / split;
    amountInput.value = (Math.round((splitAmount + Number.EPSILON) * 100) / 100).toFixed(2);
  }

  splitInput.addEventListener("input", applySplit);
  splitInput.addEventListener("change", applySplit);
});
