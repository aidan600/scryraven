// Progressive enhancement only. Answers, history and forms are server rendered.
(() => {
  const reader = document.querySelector('.reading-scroll');
  const preview = document.querySelector('#citation-preview');
  const narrow = matchMedia('(max-width: 760px)');
  let origin = null;
  let dismissTimer = null;
  let touchCitation = null;
  let suppressedFocus = null;

  function closePreview(restoreFocus = false) {
    clearTimeout(dismissTimer);
    const previous = origin;
    preview.hidden = true;
    previous?.setAttribute('aria-expanded', 'false');
    previous?.classList.remove('is-previewed');
    origin = null;
    if (restoreFocus && previous) {
      suppressedFocus = previous;
      previous.focus({preventScroll: true});
    }
  }

  function positionPreview() {
    if (!origin || preview.hidden) return;
    const anchor = origin.getBoundingClientRect();
    const card = preview.getBoundingClientRect();
    const margin = 12;
    const left = Math.min(Math.max(margin, anchor.left - 16), innerWidth - card.width - margin);
    const below = anchor.bottom + 8;
    const top = below + card.height <= innerHeight - margin ? below : Math.max(margin, anchor.top - card.height - 8);
    preview.style.left = left + 'px';
    preview.style.top = top + 'px';
  }

  function showPreview(citation) {
    const source = document.getElementById(citation.dataset.sourceId);
    if (!source) return;
    clearTimeout(dismissTimer);
    if (origin !== citation) closePreview();
    origin = citation;
    citation.setAttribute('aria-expanded', 'true');
    citation.classList.add('is-previewed');
    preview.querySelector('#citation-preview-title').textContent = source.querySelector('.source-title').textContent;
    preview.querySelector('.citation-preview-number').textContent = 'Source ' + source.querySelector('.source-number').textContent;
    preview.querySelector('.citation-preview-content').replaceChildren(...source.querySelector('.source-preview').cloneNode(true).childNodes);
    preview.querySelector('.saved-excerpt-link').href = '#' + source.id + '-excerpt';
    preview.hidden = false;
    positionPreview();
  }

  function scheduleDismiss() {
    clearTimeout(dismissTimer);
    dismissTimer = setTimeout(() => {
      if (!preview.matches(':hover') && !origin?.matches(':hover') &&
          !preview.contains(document.activeElement) && document.activeElement !== origin) closePreview();
    }, 180);
  }

  document.querySelectorAll('a.citation[data-source-id]').forEach(citation => {
    citation.addEventListener('pointerenter', event => {
      if (event.pointerType === 'touch') return;
      suppressedFocus = null;
      showPreview(citation);
    });
    citation.addEventListener('pointerleave', scheduleDismiss);
    citation.addEventListener('focus', () => {
      if (suppressedFocus !== citation) showPreview(citation);
    });
    citation.addEventListener('blur', () => { suppressedFocus = null; scheduleDismiss(); });
    citation.addEventListener('pointerdown', event => { touchCitation = event.pointerType === 'touch' ? citation : null; });
    citation.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      // A touch tap exposes the same actions without depending on hover. Mouse
      // clicks and keyboard Enter retain the direct original-publication link.
      if (touchCitation === citation || !citation.hasAttribute('target')) {
        event.preventDefault();
        showPreview(citation);
        if (event.detail === 0) preview.querySelector('.source-url a, .saved-excerpt-link').focus();
      }
      touchCitation = null;
    });
    citation.addEventListener('keydown', event => {
      if ((event.key === 'Tab' && !event.shiftKey && !preview.hidden && origin === citation) ||
          event.key === 'ArrowDown' || event.key === ' ') {
        event.preventDefault();
        showPreview(citation);
        preview.querySelector('.source-url a, .saved-excerpt-link').focus();
      }
    });
  });
  preview.addEventListener('pointerenter', () => clearTimeout(dismissTimer));
  preview.addEventListener('pointerleave', scheduleDismiss);
  preview.addEventListener('focusout', scheduleDismiss);
  preview.querySelector('.preview-close').addEventListener('click', () => closePreview(true));
  preview.querySelector('.saved-excerpt-link').addEventListener('click', event => {
    event.preventDefault();
    const excerpt = document.getElementById(event.currentTarget.hash.slice(1));
    const source = excerpt.closest('.source');
    const citationStart = origin?.dataset.citationStart;
    source.closest('.sources-overview').open = true;
    source.open = true;
    excerpt.open = true;
    excerpt.querySelectorAll('.citation-support').forEach(support => {
      support.open = support.dataset.citationStart === citationStart;
    });
    closePreview();
    excerpt.querySelector('summary').focus({preventScroll: true});
    excerpt.scrollIntoView({block: 'start', behavior: 'instant'});
  });
  preview.addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const controls = [...preview.querySelectorAll('a, button')];
    if (event.shiftKey && document.activeElement === controls[0]) {
      event.preventDefault();
      suppressedFocus = origin;
      origin.focus({preventScroll: true});
    } else if (!event.shiftKey && document.activeElement === controls.at(-1)) {
      event.preventDefault();
      const all = [...document.querySelectorAll('a[href], button, summary, textarea, input:not([type=hidden])')]
        .filter(el => !preview.contains(el) && el.getClientRects().length && !el.disabled);
      const next = all[all.indexOf(origin) + 1];
      closePreview();
      next?.focus();
    }
  });
  document.addEventListener('pointerdown', event => {
    if (!preview.hidden && !preview.contains(event.target) && !origin?.contains(event.target)) closePreview();
  });
  document.addEventListener('focusin', event => {
    if (!preview.hidden && !preview.contains(event.target) && event.target !== origin) closePreview();
  });
  reader.addEventListener('scroll', () => {
    if (origin && document.activeElement === origin) {
      const anchor = origin.getBoundingClientRect();
      const viewport = reader.getBoundingClientRect();
      if (anchor.bottom > viewport.top && anchor.top < viewport.bottom &&
          anchor.right > viewport.left && anchor.left < viewport.right) {
        positionPreview();
        return;
      }
    }
    closePreview();
  }, {passive: true});
  window.addEventListener('resize', () => closePreview());
  document.addEventListener('click', event => {
    document.querySelectorAll('.session-actions[open]').forEach(menu => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  });

  const askForm = document.querySelector('.ask-form');
  if (askForm) {
    const question = askForm.querySelector('textarea');
    const submit = askForm.querySelector('[type=submit]');
    let submitting = false;
    askForm.addEventListener('submit', event => {
      if (submitting) { event.preventDefault(); return; }
      if (!question.value.trim()) {
        event.preventDefault();
        question.setCustomValidity('Write a research question to begin.');
        question.reportValidity();
        return;
      }
      submitting = true;
      submit.disabled = true;
      question.readOnly = true;
      askForm.setAttribute('aria-busy', 'true');
      askForm.querySelector('.working-state').hidden = false;
      askForm.querySelector('.composer-caption').hidden = true;
    });
    question.addEventListener('input', () => question.setCustomValidity(''));
    question.addEventListener('keydown', event => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        askForm.requestSubmit();
      }
    });
    // Back/Forward may restore a disabled form from the browser's page cache.
    window.addEventListener('pageshow', () => {
      submitting = false;
      submit.disabled = false;
      question.readOnly = false;
      askForm.removeAttribute('aria-busy');
      askForm.querySelector('.working-state').hidden = true;
      askForm.querySelector('.composer-caption').hidden = false;
    });
  }

  const sidebar = document.querySelector('.sidebar');
  const workspace = document.querySelector('.workspace');
  const openHistory = document.querySelector('.open-history');
  function closeHistory() {
    sidebar.classList.remove('is-open');
    sidebar.removeAttribute('role');
    sidebar.removeAttribute('aria-modal');
    workspace.inert = false;
    if (location.hash === '#history') history.replaceState(null, '', location.pathname + location.search);
    openHistory.focus({preventScroll: true});
  }
  openHistory.addEventListener('click', event => {
    event.preventDefault();
    sidebar.classList.add('is-open');
    sidebar.setAttribute('role', 'dialog');
    sidebar.setAttribute('aria-modal', 'true');
    workspace.inert = true;
    sidebar.querySelector('.close-history').focus();
  });
  sidebar.querySelector('.close-history').addEventListener('click', event => { event.preventDefault(); closeHistory(); });
  sidebar.addEventListener('keydown', event => {
    if (!sidebar.classList.contains('is-open') || event.key !== 'Tab') return;
    const focusable = [...sidebar.querySelectorAll('a, summary')].filter(el => el.getClientRects().length);
    const first = focusable[0], last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  narrow.addEventListener('change', () => {
    if (sidebar.classList.contains('is-open')) closeHistory();
  });

  const rename = document.querySelector('.rename-form');
  if (rename) rename.querySelector('[name=title]').select();
  const deletion = document.querySelector('#delete-confirmation');
  if (deletion) {
    deletion.close();
    deletion.showModal();
    deletion.querySelector('.delete-cancel').focus();
    deletion.addEventListener('cancel', event => {
      event.preventDefault();
      location.href = deletion.querySelector('.delete-cancel').href;
    });
    deletion.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.target.matches('.delete-button, .delete-cancel')) event.preventDefault();
    });
  }
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (!preview.hidden) { event.preventDefault(); closePreview(true); return; }
    if (sidebar.classList.contains('is-open')) { closeHistory(); return; }
    if (rename) { location.href = rename.querySelector('.rename-cancel').href; return; }
    document.querySelectorAll('.session-actions[open]').forEach(menu => {
      menu.open = false;
      menu.querySelector('summary').focus();
    });
  });
})();
