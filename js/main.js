(() => {
  'use strict';
  document.documentElement.classList.add('js');

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  /* ---------- Rok w stopce ---------- */
  const year = $('[data-year]');
  if (year) year.textContent = new Date().getFullYear();

  /* ---------- Nawigacja mobilna ---------- */
  const toggle = $('[data-nav-toggle]');
  const navList = $('#nav-list');
  const setNav = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    navList.classList.toggle('is-open', open);
  };
  toggle?.addEventListener('click', () => setNav(toggle.getAttribute('aria-expanded') !== 'true'));
  navList?.addEventListener('click', (e) => { if (e.target.closest('a')) setNav(false); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && toggle?.getAttribute('aria-expanded') === 'true') { setNav(false); toggle.focus(); }
  });

  /* ---------- Nagłówek i pasek CTA ---------- */
  const header = $('[data-header]');
  const mobileCta = $('[data-mobile-cta]');
  const hero = $('.hero');
  const contact = $('#kontakt');
  const onScroll = () => {
    header?.classList.toggle('is-scrolled', window.scrollY > 8);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  if (mobileCta && 'IntersectionObserver' in window) {
    let heroVisible = !!hero, contactVisible = false;
    const update = () => mobileCta.classList.toggle('is-visible', !heroVisible && !contactVisible);
    update();
    if (hero) new IntersectionObserver(([e]) => { heroVisible = e.isIntersecting; update(); }).observe(hero);
    if (contact) new IntersectionObserver(([e]) => { contactVisible = e.isIntersecting; update(); }).observe(contact);
  }

  /* ---------- Animacje wejścia ---------- */
  const revealEls = $$('.section-head, .offer-card, .apartment-grid, .gallery-section, .strip-grid, .other-card,.tile, .building-copy, .building-media, .location-grid > *, .area-card, .why,.info-grid li, .contact-inner');
  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    revealEls.forEach((el) => el.classList.add('reveal'));
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { entry.target.classList.add('is-in'); io.unobserve(entry.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    revealEls.forEach((el) => io.observe(el));
  }

  /* ---------- Lightbox ---------- */
  const lb = $('[data-lightbox]');
  if (lb && typeof lb.showModal === 'function') {
    const img = $('[data-lb-img]', lb);
    const caption = $('[data-lb-caption]', lb);
    const counter = $('[data-lb-counter]', lb);
    let items = [];
    let index = 0;
    let opener = null;

    const preload = (i) => {
      const it = items[(i + items.length) % items.length];
      if (!it || it.preloaded) return;
      const p = new Image();
      p.sizes = '100vw';
      if (it.srcset) p.srcset = it.srcset;
      p.src = it.src;
      it.preloaded = true;
    };

    const render = () => {
      const it = items[index];
      img.removeAttribute('srcset');
      img.src = it.src;
      if (it.srcset) { img.srcset = it.srcset; img.sizes = '100vw'; }
      img.alt = it.alt;
      img.classList.toggle('is-plan', !!it.plan);
      caption.textContent = it.alt;
      counter.textContent = `${index + 1} / ${items.length}`;
      preload(index + 1);
      preload(index - 1);
    };

    const open = (list, start, from) => {
      items = list;
      index = start;
      opener = from;
      lb.classList.toggle('is-single', items.length < 2);
      render();
      lb.showModal();
      document.body.style.overflow = 'hidden';
    };
    const close = () => lb.close();
    const step = (d) => { if (items.length > 1) { index = (index + d + items.length) % items.length; render(); } };

    lb.addEventListener('close', () => {
      document.body.style.overflow = '';
      img.removeAttribute('src');
      opener?.focus();
    });
    $('[data-lb-close]', lb).addEventListener('click', close);
    $('[data-lb-prev]', lb).addEventListener('click', () => step(-1));
    $('[data-lb-next]', lb).addEventListener('click', () => step(1));
    lb.addEventListener('click', (e) => { if (e.target === lb || e.target.classList.contains('lightbox-figure')) close(); });
    lb.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') step(-1);
      if (e.key === 'ArrowRight') step(1);
    });

    // Gesty przesuwania na ekranach dotykowych
    let x0 = null, y0 = null;
    lb.addEventListener('touchstart', (e) => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    lb.addEventListener('touchend', (e) => {
      if (x0 === null) return;
      const dx = e.changedTouches[0].clientX - x0;
      const dy = e.changedTouches[0].clientY - y0;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) step(dx < 0 ? 1 : -1);
      else if (dy > 90 && Math.abs(dy) > Math.abs(dx)) close();
      x0 = y0 = null;
    }, { passive: true });

    // Galerie apartamentów: siatka [data-gallery] jest źródłem listy zdjęć
    const galleries = {};
    $$('[data-gallery]').forEach((gallery) => {
      const links = $$('a', gallery);
      const list = links.map((a) => ({
        src: a.getAttribute('href'),
        srcset: a.dataset.srcset || '',
        alt: a.dataset.alt || a.querySelector('img')?.alt || '',
      }));
      galleries[gallery.dataset.gallery] = list;
      links.forEach((a, i) => {
        a.addEventListener('click', (e) => { e.preventDefault(); open(list, i, a); });
      });
    });

    // Kafelki u góry strony otwierają galerię od wskazanego zdjęcia
    $$('[data-gallery-open]').forEach((a) => {
      a.addEventListener('click', (e) => {
        const list = galleries[a.dataset.galleryOpen];
        if (!list) return;
        e.preventDefault();
        open(list, Number(a.dataset.index) || 0, a);
      });
    });

    // Rzuty mieszkań
    $$('[data-plan]').forEach((btn) => {
      btn.addEventListener('click', () => open([{ src: btn.dataset.plan, alt: btn.dataset.planAlt, plan: true }], 0, btn));
    });
  }

  /* ---------- Filmy w tle (bez dźwięku, grają tylko gdy są widoczne) ---------- */
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const bgVideos = $$('video[data-autoplay]');
  const tryPlay = (v) => { const p = v.play(); if (p) p.catch(() => {}); };
  if (!reduceMotion && 'IntersectionObserver' in window) {
    const vio = new IntersectionObserver((entries) => {
      entries.forEach(({ target: v, isIntersecting }) => {
        if (v.dataset.full) return;
        if (isIntersecting) tryPlay(v); else v.pause();
      });
    }, { threshold: 0.25 });
    bgVideos.forEach((v) => vio.observe(v));
  }

  // „Obejrzyj film z dźwiękiem” – od początku, z dźwiękiem i sterowaniem, na pełnym ekranie
  $$('[data-video-full]').forEach((btn) => {
    const v = btn.parentElement.querySelector('video');
    const fsElement = () => document.fullscreenElement || document.webkitFullscreenElement;
    const back = () => {
      delete v.dataset.full;
      v.muted = true; v.controls = false; v.loop = true;
      btn.hidden = false;
      if (reduceMotion) v.pause(); else tryPlay(v);
    };
    btn.addEventListener('click', () => {
      v.dataset.full = '1';
      v.currentTime = 0; v.muted = false; v.loop = false; v.controls = true;
      btn.hidden = true;
      tryPlay(v);
      if (v.requestFullscreen) v.requestFullscreen().catch(() => {});
      else if (v.webkitEnterFullscreen) v.webkitEnterFullscreen();
    });
    document.addEventListener('fullscreenchange', () => { if (!fsElement() && v.dataset.full) back(); });
    v.addEventListener('webkitendfullscreen', back);
    v.addEventListener('ended', () => { if (v.dataset.full) { if (fsElement()) document.exitFullscreen?.(); back(); } });
  });

  /* ---------- Mapa (ładowana na żądanie) ---------- */
  const mapBtn = $('[data-map-load]');
  mapBtn?.addEventListener('click', () => {
    const lat = 51.114017, lon = 17.02036, d = 0.008;
    const iframe = document.createElement('iframe');
    iframe.title = 'Mapa – Quorum Apartments, ul. Sikorskiego 13, Wrocław';
    iframe.loading = 'lazy';
    iframe.referrerPolicy = 'no-referrer';
    iframe.src = `https://www.openstreetmap.org/export/embed.html?bbox=${lon - d * 1.6},${lat - d},${lon + d * 1.6},${lat + d}&layer=mapnik&marker=${lat},${lon}`;
    mapBtn.replaceWith(iframe);
  });
})();
