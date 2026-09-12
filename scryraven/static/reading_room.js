// Progressive enhancement only. Answers, history and forms are server rendered.
(() => {
  const reader = document.querySelector('.reading-scroll');
  const inspector = document.querySelector('#evidence-inspector');
  const inspectorContent = inspector.querySelector('.inspector-content');
  const inspectorTitle = inspector.querySelector('#inspector-title');
  const inspectorNumber = inspector.querySelector('.inspector-number');
  const inspectorScroll = inspector.querySelector('.inspector-scroll');
  const wide = matchMedia('(min-width: 1700px)');
  const narrow = matchMedia('(max-width: 760px)');
  let origin = null;
  let sourceGroup = null;
  let readingPosition = 0;

  function showInspector() {
    if (!inspector.open) {
      readingPosition = reader.scrollTop;
      document.body.classList.add('evidence-open');
      if (wide.matches) inspector.show();
      else inspector.showModal();
      reader.scrollTop = readingPosition;
    }
    inspectorScroll.scrollTop = 0;
    inspector.querySelector('.inspector-close').focus({preventScroll: true});
  }

  function showSource(source) {
    sourceGroup = source.closest('.sources-overview');
    inspectorTitle.textContent = source.querySelector('.source-title').textContent;
    inspectorNumber.textContent = 'Source ' + source.querySelector('.source-number').textContent;
    inspectorContent.replaceChildren(...source.querySelector('.source-body').cloneNode(true).childNodes);
    inspector.classList.add('showing-source');
    showInspector();
  }

  function showOverview(group) {
    sourceGroup = group;
    inspectorTitle.textContent = 'Sources for this answer';
    inspectorNumber.textContent = 'The reading behind the answer';
    inspectorContent.replaceChildren();
    group.querySelectorAll('.source').forEach(source => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'overview-source';
      button.append(source.querySelector('.source-number').cloneNode(true));
      const title = document.createElement('span');
      title.textContent = source.querySelector('.source-title').textContent;
      button.append(title);
      button.addEventListener('click', () => showSource(source));
      inspectorContent.append(button);
    });
    inspector.classList.remove('showing-source');
    showInspector();
  }

  document.addEventListener('click', event => {
    const citation = event.target.closest('a.citation');
    if (citation) {
      const source = document.getElementById(citation.hash.slice(1));
      if (!source || !source.matches('.source')) return;
      event.preventDefault();
      origin?.classList.remove('is-inspected');
      origin = citation;
      origin.classList.add('is-inspected');
      showSource(source);
    }
    const overview = event.target.closest('.sources-control');
    if (overview) {
      event.preventDefault();
      origin?.classList.remove('is-inspected');
      origin = overview;
      showOverview(overview.closest('.sources-overview'));
    }
    document.querySelectorAll('.session-actions[open]').forEach(menu => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  });
  inspector.querySelector('.inspector-back').addEventListener('click', () => showOverview(sourceGroup));
  inspector.querySelector('.inspector-close').addEventListener('click', () => inspector.close());
  inspector.addEventListener('close', () => {
    document.body.classList.remove('evidence-open');
    reader.scrollTop = readingPosition;
    origin?.classList.remove('is-inspected');
    origin?.focus({preventScroll: true});
  });
  reader.addEventListener('scroll', () => {
    if (inspector.open) readingPosition = reader.scrollTop;
  }, {passive: true});
  // Close when changing between dock and sheet so modal/focus state stays sound.
  wide.addEventListener('change', () => {
    if (!inspector.open) return;
    inspector.close();
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
    if (inspector.open) { inspector.close(); return; }
    if (sidebar.classList.contains('is-open')) { closeHistory(); return; }
    if (rename) { location.href = rename.querySelector('.rename-cancel').href; return; }
    document.querySelectorAll('.session-actions[open]').forEach(menu => {
      menu.open = false;
      menu.querySelector('summary').focus();
    });
  });
})();
