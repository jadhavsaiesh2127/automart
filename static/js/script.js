

// AutoMart UI enhancements
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("img").forEach(img => {
    if (!img.getAttribute("loading")) img.setAttribute("loading", "lazy");
  });

  const nav = document.querySelector(".navbar");
  const onScroll = () => {
    if (nav) nav.style.boxShadow = window.scrollY > 8
      ? "0 7px 24px rgba(0,0,0,.20)"
      : "0 4px 18px rgba(0,0,0,.16)";
  };
  window.addEventListener("scroll", onScroll);
  onScroll();

  document.querySelectorAll('form button[type="submit"]').forEach(btn => {
    btn.addEventListener("click", () => {
      if (btn.form && btn.form.checkValidity()) {
        btn.dataset.originalText = btn.innerHTML;
        if (!btn.dataset.noLoading) {
          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Processing...';
        }
      }
    });
  });
});
