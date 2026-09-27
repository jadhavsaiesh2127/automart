document.addEventListener("DOMContentLoaded", () => {
  const tabs = document.querySelectorAll(".pay-method-tab");
  const panels = document.querySelectorAll(".pay-panel");
  const methodInput = document.getElementById("selected-method");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const method = tab.dataset.method;
      tabs.forEach((t) => t.classList.remove("active"));
      panels.forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      const panel = document.getElementById(`panel-${method}`);
      if (panel) panel.classList.add("active");
      if (methodInput) methodInput.value = method;
    });
  });

  // Delivery type radio -> live-update the fee shown in the summary card
  const deliveryRadios = document.querySelectorAll("input[name=delivery_type]");
  const feeDisplay = document.getElementById("delivery-fee-display");
  const totalDisplay = document.getElementById("total-display");
  const subtotalEl = document.getElementById("subtotal-value");

  function refreshDeliveryPreview() {
    const checked = document.querySelector("input[name=delivery_type]:checked");
    if (!checked || !feeDisplay || !totalDisplay || !subtotalEl) return;
    const fee = parseInt(checked.dataset.fee || "0", 10);
    const subtotal = parseInt(subtotalEl.dataset.value || "0", 10);
    feeDisplay.textContent = fee === 0 ? "Free" : `₹${fee}`;
    totalDisplay.textContent = `₹${subtotal + fee}`;
  }

  deliveryRadios.forEach((r) => r.addEventListener("change", refreshDeliveryPreview));
  refreshDeliveryPreview();
});
