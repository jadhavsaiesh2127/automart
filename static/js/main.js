document.addEventListener("DOMContentLoaded", () => {
  // Auto-dismiss flash messages
  const stack = document.getElementById("flash-stack");
  if (stack) {
    setTimeout(() => {
      stack.style.transition = "opacity 0.4s";
      stack.style.opacity = "0";
      setTimeout(() => stack.remove(), 400);
    }, 3200);
  }

  // AJAX "add to cart" buttons (data-ajax-cart-form)
  document.querySelectorAll("form[data-ajax-cart-form]").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = form.querySelector("button[type=submit]");
      const originalText = btn ? btn.textContent : "";
      if (btn) { btn.disabled = true; btn.textContent = "Adding..."; }

      try {
        const res = await fetch(form.action, {
          method: "POST",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          body: new FormData(form),
        });
        const data = await res.json();
        if (data.ok) {
          document.querySelectorAll("[data-cart-count]").forEach((el) => (el.textContent = data.cart_count));
          if (btn) btn.textContent = "Added ✓";
          setTimeout(() => { if (btn) { btn.disabled = false; btn.textContent = originalText; } }, 1200);
        }
      } catch (err) {
        if (btn) { btn.disabled = false; btn.textContent = originalText; }
      }
    });
  });
});
