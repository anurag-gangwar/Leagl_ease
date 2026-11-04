/* ═══════════════════════════════════════════
   Legal-Ease — Main JavaScript
═══════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  // ── Auto-dismiss toasts ──
  document.querySelectorAll('.toast').forEach(toast => {
    setTimeout(() => {
      try { bootstrap.Toast.getOrCreateInstance(toast).hide(); }
      catch (e) { toast.style.display = 'none'; }
    }, 4500);
  });

  // ── Active nav highlighting ──
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  // ── Scroll-triggered fade-in for cards ──
  const fadeElements = document.querySelectorAll(
    '.step-card, .flag-card, .contract-card, .metric-card, .analysis-panel'
  );

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity   = '1';
          entry.target.style.transform = 'translateY(0)';
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });

    fadeElements.forEach(el => {
      el.style.opacity   = '0';
      el.style.transform = 'translateY(16px)';
      el.style.transition = 'opacity 0.45s ease, transform 0.45s ease';
      observer.observe(el);
    });
  }

  // ── Smooth scroll for anchor links ──
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        const offset = 80; // nav height
        const top = target.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  });

  // ── Sticky nav shadow on scroll ──
  const nav = document.getElementById('mainNav');
  if (nav) {
    window.addEventListener('scroll', () => {
      nav.style.boxShadow = window.scrollY > 10
        ? '0 4px 24px rgba(0,0,0,.35)'
        : '0 2px 16px rgba(0,0,0,.3)';
    }, { passive: true });
  }

  // ── Table row highlight on hover ──
  document.querySelectorAll('.contract-row').forEach(row => {
    row.style.transition = 'background 0.18s ease';
  });

  // ── Copy-to-clipboard for code blocks ──
  document.querySelectorAll('code').forEach(block => {
    block.style.cursor = 'pointer';
    block.title = 'Click to copy';
    block.addEventListener('click', () => {
      navigator.clipboard.writeText(block.textContent).then(() => {
        const orig = block.textContent;
        block.textContent = '✓ Copied!';
        setTimeout(() => { block.textContent = orig; }, 1500);
      });
    });
  });

  // ── Bootstrap tooltips ──
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el, { trigger: 'hover', delay: { show: 300, hide: 100 } });
  });

});

/* ── Jinja2 nl2br filter polyfill (use in templates) ── */
/* Handled server-side via template filter below */
