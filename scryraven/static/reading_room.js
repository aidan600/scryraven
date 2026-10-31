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
    const content = source.querySelector('.source-preview').cloneNode(true);
    const description = content.querySelector('.citation-description');
    const title = source.querySelector('.source-title').textContent;
    const heading = preview.querySelector('#citation-preview-title');
    heading.textContent = description?.textContent || title;
    heading.classList.toggle('has-description', Boolean(description));
    const originalTitle = preview.querySelector('.citation-original-title');
    originalTitle.textContent = title;
    originalTitle.hidden = !description;
    description?.remove();
    preview.querySelector('.citation-preview-number').textContent = 'Source ' + source.querySelector('.source-number').textContent;
    preview.querySelector('.citation-preview-content').replaceChildren(...content.childNodes);
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
  let saveDraft = () => {};
  if (askForm) {
    const question = askForm.querySelector('textarea');
    const submit = askForm.querySelector('[type=submit]');
    const picker = askForm.querySelector('[type=file]');
    const composer = askForm.querySelector('.composer');
    const chips = askForm.querySelector('.attachment-chips');
    const error = askForm.querySelector('.composer-error');
    const recovery = askForm.querySelector('.submission-recovery');
    const announcement = askForm.querySelector('.composer-status');
    const preferences = askForm.querySelector('.composer-preferences');
    const draftKey = 'scryraven-draft:' + askForm.dataset.draftKey;
    let submitting = false;
    let files = [];
    let objectURLs = [];
    let dragDepth = 0;
    let uploadProblem = '';
    const activeJob = ['queued', 'researching'].includes(document.body.dataset.jobState);
    if (activeJob) {
      submit.disabled = true;
      submit.title = 'This conversation is still researching. Your draft will be kept.';
    }
    function expand() {
      question.style.height = 'auto';
      question.style.height = Math.max(44, Math.min(question.scrollHeight, 240, innerHeight * .35)) + 'px';
    }
    saveDraft = () => {
      try {
        if (question.value) sessionStorage.setItem(draftKey, question.value);
        else sessionStorage.removeItem(draftKey);
      } catch (_) { /* A private browser may disable local draft storage. */ }
    };
    try {
      if (!question.value) question.value = sessionStorage.getItem(draftKey) || '';
    } catch (_) { /* The server-rendered form remains usable without storage. */ }
    expand();
    function showError(message) {
      error.textContent = message;
      error.hidden = !message;
    }
    function syncFiles() {
      const transfer = new DataTransfer();
      files.forEach(file => transfer.items.add(file));
      picker.files = transfer.files;
    }
    function drawFiles() {
      objectURLs.forEach(url => URL.revokeObjectURL(url));
      objectURLs = [];
      chips.replaceChildren();
      chips.hidden = !files.length;
      files.forEach((file, index) => {
        const chip = document.createElement('div');
        chip.className = 'attachment-chip';
        chip.setAttribute('role', 'listitem');
        if (['image/png', 'image/jpeg', 'image/webp'].includes(file.type) && file.size <= 8 * 1048576) {
          const thumbnail = document.createElement('img');
          const url = URL.createObjectURL(file);
          objectURLs.push(url);
          thumbnail.src = url;
          thumbnail.alt = '';
          chip.append(thumbnail);
        }
        const identity = document.createElement('span');
        const name = document.createElement('span');
        name.className = 'attachment-chip-name';
        name.textContent = file.name;
        const detail = document.createElement('small');
        detail.textContent = (file.type === 'application/pdf' ? 'PDF · text analysis' : file.type.replace('image/', '').toUpperCase()) +
          ' · ' + (file.size >= 1048576 ? (file.size / 1048576).toFixed(1) + ' MB' : Math.ceil(file.size / 1024) + ' KB');
        identity.append(name, detail);
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'remove-attachment';
        remove.textContent = '×';
        remove.setAttribute('aria-label', 'Remove ' + file.name);
        remove.addEventListener('click', () => {
          files.splice(index, 1);
          syncFiles();
          uploadProblem = validateFiles(files);
          showError(uploadProblem);
          drawFiles();
          announcement.textContent = 'Attachment removed.';
          question.focus();
        });
        chip.append(identity, remove);
        chips.append(chip);
      });
    }
    function validateFiles(combined) {
      if (combined.length > 4) return 'Choose at most four attachments per question. Remove extra files before sending.';
      for (const file of combined) {
        if (!['application/pdf', 'image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
          return 'Only text PDFs and PNG, JPEG or WebP images are supported. Remove unsupported files before sending.';
        }
        const maximum = file.type === 'application/pdf' ? 20 : 8;
        if (file.size > maximum * 1048576) {
          return file.name + ' is too large. ' + (file.type === 'application/pdf' ? 'PDFs' : 'Images') + ' must be at most ' + maximum + ' MB. Remove this file before sending.';
        }
      }
      if (combined.reduce((total, file) => total + file.size, 0) > 24 * 1048576) {
        return 'Attachments must total at most 24 MB per question. Remove files before sending.';
      }
      return '';
    }
    function addFiles(incoming) {
      if (submitting) return;
      const additions = [...incoming];
      if (!additions.length) return;
      files = [...files, ...additions];
      uploadProblem = validateFiles(files);
      syncFiles();
      drawFiles();
      showError(uploadProblem);
      announcement.textContent = additions.length + (additions.length === 1 ? ' attachment added.' : ' attachments added.');
    }
    picker.addEventListener('change', () => addFiles(picker.files));
    ['dragenter', 'dragover'].forEach(type => composer.addEventListener(type, event => {
      if (!event.dataTransfer?.types.includes('Files')) return;
      event.preventDefault();
      if (type === 'dragenter') dragDepth++;
      composer.classList.add('is-dragging');
      event.dataTransfer.dropEffect = 'copy';
    }));
    composer.addEventListener('dragleave', event => {
      event.preventDefault();
      if (--dragDepth <= 0) { dragDepth = 0; composer.classList.remove('is-dragging'); }
    });
    composer.addEventListener('drop', event => {
      if (!event.dataTransfer?.files.length) return;
      event.preventDefault();
      dragDepth = 0;
      composer.classList.remove('is-dragging');
      addFiles(event.dataTransfer.files);
      question.focus();
    });
    question.addEventListener('paste', event => {
      const images = [...(event.clipboardData?.items || [])].filter(item => item.kind === 'file').map(item => item.getAsFile()).filter(Boolean);
      if (!images.length) return;
      event.preventDefault();
      addFiles(images);
    });
    askForm.addEventListener('submit', async event => {
      event.preventDefault();
      if (submitting || activeJob) return;
      if (uploadProblem) { showError(uploadProblem); return; }
      if (!question.value.trim()) {
        question.setCustomValidity('Write a research question to begin.');
        question.reportValidity();
        return;
      }
      if (!askForm.reportValidity()) return;
      submitting = true;
      submit.disabled = true;
      question.readOnly = true;
      picker.disabled = true;
      askForm.setAttribute('aria-busy', 'true');
      announcement.textContent = 'Submitting your question and attachments.';
      showError('');
      recovery.hidden = true;
      recovery.replaceChildren();
      preferences.open = false;
      // Snapshot every file with the question before disabling picker controls.
      const body = new FormData(askForm);
      body.delete('files');
      files.forEach(file => body.append('files', file, file.name));
      try {
        const response = await fetch(askForm.action, {method: 'POST', body, credentials: 'same-origin'});
        if (!response.ok) {
          const rendered = new DOMParser().parseFromString(await response.text(), 'text/html');
          showError(rendered.querySelector('.error-notice')?.textContent.trim() || 'Your question could not be accepted. Your text and selected files are still here.');
          const replacement = rendered.querySelector('.ask-form [name=form_token]');
          if (replacement) askForm.querySelector('[name=form_token]').value = replacement.value;
          if (response.headers.get('X-ScryRaven-Submission-Conflict') === '1') {
            const location = response.headers.get('X-ScryRaven-Submission-Location');
            const accepted = location ? new URL(location, window.location.origin) : null;
            if (accepted?.origin === window.location.origin && /^\/sessions\/[a-f0-9]{32}$/.test(accepted.pathname)) {
              const link = document.createElement('a');
              link.href = accepted.href;
              link.textContent = 'Open the previously accepted question';
              recovery.append(link);
            }
            const newKey = rendered.querySelector('.ask-form [name=idempotency_key]')?.value;
            if (newKey) {
              const reset = document.createElement('button');
              reset.type = 'button';
              reset.className = 'small-button';
              reset.textContent = 'Use a new submission for this draft';
              reset.addEventListener('click', () => {
                askForm.querySelector('[name=idempotency_key]').value = newKey;
                reset.remove();
                showError('Your earlier question remains saved. This draft now has a new submission identity; send it when ready.');
                question.focus();
              });
              recovery.append(reset);
            }
            recovery.hidden = !recovery.childElementCount;
          }
          announcement.textContent = 'Question not sent. Review the error and retry.';
          return;
        }
        if (!response.redirected) {
          showError('The server did not confirm a saved research run. Your question and files are still here.');
          return;
        }
        try { sessionStorage.removeItem(draftKey); } catch (_) {}
        question.value = '';
        location.assign(response.url);
      } catch (_) {
        showError('Connection interrupted. Your question and selected files are still here. Retry uses the same submission identity.');
      } finally {
        submitting = false;
        submit.disabled = false;
        question.readOnly = false;
        picker.disabled = false;
        askForm.removeAttribute('aria-busy');
      }
    });
    question.addEventListener('input', () => {
      question.setCustomValidity('');
      expand();
      saveDraft();
    });
    question.addEventListener('keydown', event => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        askForm.requestSubmit();
      }
    });
    document.addEventListener('pointerdown', event => {
      if (preferences.open && !preferences.contains(event.target)) preferences.open = false;
    });
    preferences.addEventListener('keydown', event => {
      if (event.key === 'Escape') { preferences.open = false; preferences.querySelector('summary').focus(); }
    });
    window.addEventListener('pagehide', saveDraft);
    window.addEventListener('pageshow', () => {
      submitting = false;
      submit.disabled = activeJob;
      question.readOnly = false;
      picker.disabled = false;
      askForm.removeAttribute('aria-busy');
      expand();
    });
  }

  const stateLabels = {queued: 'Queued', researching: 'Researching', completed: 'Completed', failed: 'Failed', interrupted: 'Interrupted'};
  const knownJobs = new Map();
  document.querySelectorAll('.session-row[data-session-id]').forEach(row => {
    knownJobs.set(row.dataset.sessionId, row.querySelector('.session-job-state')?.dataset.state || '');
  });
  const notifications = document.querySelector('.research-notifications');
  if (location.hash === '#research-status') {
    const pending = document.querySelector('#research-status');
    if (pending) {
      pending.focus({preventScroll: true});
      pending.scrollIntoView({block: 'start'});
    } else if (document.body.dataset.jobState === 'completed') {
      history.replaceState(null, '', '#turn-' + document.body.dataset.revision);
    }
  }
  if (document.body.dataset.jobState === 'completed' && /^#turn-\d+$/.test(location.hash)) {
    const completed = document.querySelector(location.hash);
    completed?.querySelector('h2').focus({preventScroll: true});
    completed?.scrollIntoView({block: 'start'});
  }
  function notifyJob(job) {
    notifications.replaceChildren();
    const message = document.createElement('span');
    message.textContent = job.state === 'completed' ? 'Research completed. ' : 'Research ' + stateLabels[job.state].toLowerCase() + '. ';
    const link = document.createElement('a');
    link.href = '/sessions/' + encodeURIComponent(job.session_id);
    link.textContent = 'Open conversation';
    notifications.append(message, link);
  }
  async function pollJobs() {
    try {
      const response = await fetch('/jobs/status', {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
      if (response.ok) {
        const status = await response.json();
        for (const job of status.jobs || []) {
          const previous = knownJobs.get(job.session_id);
          knownJobs.set(job.session_id, job.state);
          const row = [...document.querySelectorAll('.session-row[data-session-id]')].find(item => item.dataset.sessionId === job.session_id);
          const badge = row?.querySelector('.session-job-state');
          if (badge) { badge.textContent = stateLabels[job.state] || ''; badge.dataset.state = job.state; badge.hidden = !stateLabels[job.state]; }
          const isCurrent = job.session_id === document.body.dataset.sessionId && job.job_id === document.body.dataset.jobId;
          if (isCurrent && ['queued', 'researching'].includes(document.body.dataset.jobState)) {
            if (['completed', 'failed', 'interrupted'].includes(job.state)) {
              saveDraft();
              if (job.state === 'completed') history.replaceState(null, '', '#turn-' + (job.revision + 1));
              location.reload();
              return;
            }
            if (job.state === 'researching') {
              const message = document.querySelector('.research-job .job-message');
              if (message) {
                message.querySelector('strong').textContent = 'Researching';
                message.querySelector('p').textContent = 'ScryRaven is working on your question. You can open another conversation while this continues.';
              }
            }
          } else if (['queued', 'researching'].includes(previous) && ['completed', 'failed', 'interrupted'].includes(job.state)) {
            notifyJob(job);
          }
        }
      }
    } catch (_) { /* A disconnected browser does not determine the job state. */ }
    setTimeout(pollJobs, document.hidden ? 4000 : 1500);
  }
  if (document.querySelector('.history-list')) pollJobs();

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
