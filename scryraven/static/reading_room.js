// Progressive enhancement only. Answers, history and forms are server rendered.
(() => {
  const reader = document.querySelector('.reading-scroll');
  const preview = document.querySelector('#citation-preview');
  const narrow = matchMedia('(max-width: 760px)');
  const withoutHover = matchMedia('(hover: none)');
  let origin = null;
  let dismissTimer = null;
  let touchCitation = null;
  let tappedPreview = false;
  let excerptReturn = null;
  let suppressedFocus = null;

  function closePreview(restoreFocus = false) {
    clearTimeout(dismissTimer);
    const previous = origin;
    preview.hidden = true;
    previous?.setAttribute('aria-expanded', 'false');
    previous?.classList.remove('is-previewed');
    origin = null;
    tappedPreview = false;
    if (restoreFocus && previous) {
      suppressedFocus = previous;
      previous.focus({preventScroll: true});
    }
  }

  function positionPreview() {
    if (!origin || preview.hidden) return;
    const anchor = origin.getBoundingClientRect();
    const viewport = window.visualViewport;
    const margin = 12;
    const minX = (viewport?.offsetLeft ?? 0) + margin;
    const minY = (viewport?.offsetTop ?? 0) + margin;
    const maxX = minX + (viewport?.width ?? innerWidth) - 2 * margin;
    const maxY = minY + (viewport?.height ?? innerHeight) - 2 * margin;
    preview.style.maxWidth = Math.max(0, maxX - minX) + 'px';
    preview.style.maxHeight = Math.max(0, Math.min(520, maxY - minY)) + 'px';
    const card = preview.getBoundingClientRect();
    const left = Math.max(minX, Math.min(anchor.left - 16, maxX - card.width));
    const below = anchor.bottom + 8;
    const preferredTop = below + card.height <= maxY ? below : anchor.top - card.height - 8;
    const top = Math.max(minY, Math.min(preferredTop, maxY - card.height));
    preview.style.left = left + 'px';
    preview.style.top = top + 'px';
  }

  function showPreview(citation) {
    const source = document.getElementById(citation.dataset.sourceId);
    if (!source) return;
    clearTimeout(dismissTimer);
    if (origin === citation) {
      positionPreview();
      return;
    }
    closePreview();
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
    preview.scrollTop = 0;
    positionPreview();
  }

  function scheduleDismiss() {
    clearTimeout(dismissTimer);
    dismissTimer = setTimeout(() => {
      if (!tappedPreview && !preview.matches(':hover') && !origin?.matches(':hover') &&
          !preview.contains(document.activeElement) && document.activeElement !== origin) closePreview();
    }, 180);
  }

  function focusPreviewControl(control) {
    control.focus({preventScroll: true});
    const bounds = control.getBoundingClientRect();
    const card = preview.getBoundingClientRect();
    if (bounds.top < card.top + 4) preview.scrollTop += bounds.top - card.top - 4;
    else if (bounds.bottom > card.bottom - 4) preview.scrollTop += bounds.bottom - card.bottom + 4;
  }

  document.querySelectorAll('a.citation[data-source-id]').forEach(citation => {
    citation.tabIndex = 0;
    citation.setAttribute('aria-controls', preview.id);
    citation.setAttribute('aria-haspopup', 'dialog');
    citation.setAttribute('aria-expanded', 'false');
    citation.addEventListener('pointerenter', event => {
      if (event.pointerType !== 'mouse' || withoutHover.matches) return;
      suppressedFocus = null;
      showPreview(citation);
    });
    citation.addEventListener('pointerleave', scheduleDismiss);
    citation.addEventListener('focus', () => {
      if (suppressedFocus !== citation) showPreview(citation);
    });
    citation.addEventListener('blur', () => { suppressedFocus = null; scheduleDismiss(); });
    citation.addEventListener('pointerdown', event => {
      touchCitation = ['touch', 'pen'].includes(event.pointerType) ? citation : null;
    });
    citation.addEventListener('pointercancel', () => { touchCitation = null; });
    citation.addEventListener('click', event => {
      // WebKit can report a touch-generated click as a mouse event.
      const tapped = touchCitation === citation || withoutHover.matches ||
        ['touch', 'pen'].includes(event.pointerType);
      touchCitation = null;
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      if (tapped || citation.hasAttribute('data-preview-on-click') || !citation.hasAttribute('target')) {
        event.preventDefault();
        showPreview(citation);
        tappedPreview = tapped && event.detail !== 0;
        if (event.detail === 0) focusPreviewControl(preview.querySelector('.source-url a, .saved-excerpt-link'));
      }
    });
    citation.addEventListener('keydown', event => {
      if ((event.key === 'Tab' && !event.shiftKey && !preview.hidden && origin === citation) ||
          event.key === 'ArrowDown' || event.key === ' ') {
        event.preventDefault();
        showPreview(citation);
        focusPreviewControl(preview.querySelector('.source-url a, .saved-excerpt-link'));
      }
    });
    if (document.activeElement === citation) showPreview(citation);
  });
  preview.addEventListener('pointerenter', () => clearTimeout(dismissTimer));
  preview.addEventListener('pointerleave', scheduleDismiss);
  preview.addEventListener('focusout', scheduleDismiss);
  preview.querySelector('.preview-close').addEventListener('click', () => closePreview(true));
  function scrollReaderTo(target, offset) {
    reader.scrollTop += target.getBoundingClientRect().top - reader.getBoundingClientRect().top - offset;
  }
  preview.querySelector('.saved-excerpt-link').addEventListener('click', event => {
    event.preventDefault();
    const excerpt = document.getElementById(event.currentTarget.hash.slice(1));
    const source = excerpt.closest('.source');
    const overview = source.closest('.sources-overview');
    const citationStart = origin?.dataset.citationStart;
    if (origin) {
      excerptReturn = {overview, citation: origin, offset: origin.getBoundingClientRect().top - reader.getBoundingClientRect().top};
    }
    overview.open = true;
    source.open = true;
    excerpt.open = true;
    excerpt.querySelectorAll('.citation-support').forEach(support => {
      support.open = support.dataset.citationStart === citationStart;
    });
    closePreview();
    excerpt.querySelector('summary').focus({preventScroll: true});
    scrollReaderTo(excerpt, 20);
  });
  reader.querySelectorAll('.back-to-answer').forEach(link => {
    link.tabIndex = 0;
    link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const previous = excerptReturn?.overview === link.closest('.sources-overview') ? excerptReturn : null;
      const target = previous?.citation ?? document.getElementById(link.hash.slice(1));
      if (!target) return;
      event.preventDefault();
      excerptReturn = null;
      suppressedFocus = previous?.citation ?? null;
      target.focus({preventScroll: true});
      scrollReaderTo(target, previous?.offset ?? 20);
    });
  });
  preview.addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const controls = [...preview.querySelectorAll('a, button')];
    const current = controls.indexOf(document.activeElement);
    if (current < 0) return;
    event.preventDefault();
    const nextControl = controls[current + (event.shiftKey ? -1 : 1)];
    if (nextControl) {
      focusPreviewControl(nextControl);
    } else if (event.shiftKey) {
      suppressedFocus = origin;
      origin.focus({preventScroll: true});
    } else {
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
    if (origin && (tappedPreview || document.activeElement === origin || preview.contains(document.activeElement))) {
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
  window.addEventListener('resize', positionPreview);
  window.visualViewport?.addEventListener('resize', positionPreview);
  window.visualViewport?.addEventListener('scroll', positionPreview);
  document.addEventListener('click', event => {
    document.querySelectorAll('.session-actions[open]').forEach(menu => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  });
  function closeActionMenus(restoreFocus = false) {
    document.querySelectorAll('.session-actions[open]').forEach(menu => {
      menu.open = false;
      menu.querySelector('summary').setAttribute('aria-expanded', 'false');
      if (restoreFocus) menu.querySelector('summary').focus({preventScroll: true});
    });
  }
  document.querySelectorAll('.session-actions').forEach(menu => {
    const summary = menu.querySelector('summary');
    const popup = menu.querySelector('.action-menu');
    summary.setAttribute('aria-expanded', 'false');
    summary.addEventListener('click', event => {
      // Own the opening click so the new popup cannot receive that same tap.
      event.preventDefault();
      event.stopPropagation();
      const opening = !menu.open;
      closeActionMenus();
      if (!opening) return;
      menu.open = true;
      summary.setAttribute('aria-expanded', 'true');
      const anchor = summary.getBoundingClientRect();
      const card = popup.getBoundingClientRect();
      popup.style.left = Math.max(8, Math.min(anchor.right - card.width, innerWidth - card.width - 8)) + 'px';
      const below = anchor.bottom + 5;
      popup.style.top = (below + card.height <= innerHeight - 8 ? below : Math.max(8, anchor.top - card.height - 5)) + 'px';
    });
    summary.addEventListener('keydown', event => {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        if (!menu.open) summary.click();
        popup.querySelector('a').focus();
      }
    });
    menu.addEventListener('toggle', () => summary.setAttribute('aria-expanded', String(menu.open)));
  });
  document.querySelector('.history-list')?.addEventListener('scroll', () => closeActionMenus(), {passive: true});
  window.addEventListener('resize', () => closeActionMenus());

  const askForm = document.querySelector('.ask-form');
  let feedbackSubmitting = 0;
  function bindFeedback(section) {
    section.querySelectorAll('form').forEach(form => {
      form.addEventListener('submit', async event => {
        event.preventDefault();
        if (section.dataset.submitting) return;
        section.dataset.submitting = 'true';
        feedbackSubmitting += 1;
        const draft = section.querySelector('textarea');
        const retainedDraft = form.classList.contains('feedback-remove-form') ? draft?.value : null;
        if (draft) draft.readOnly = true;
        section.querySelectorAll('button').forEach(button => { button.disabled = true; });
        const error = section.querySelector('.feedback-error');
        if (error) error.hidden = true;
        try {
          const response = await fetch(form.action, {
            method: 'POST', credentials: 'same-origin',
            body: new URLSearchParams(new FormData(form)),
          });
          const rendered = new DOMParser().parseFromString(await response.text(), 'text/html');
          const replacement = rendered.getElementById(section.id);
          if (!replacement) throw new Error('feedback_unavailable');
          if (retainedDraft !== null && replacement.querySelector('textarea')) {
            replacement.querySelector('textarea').value = retainedDraft;
          }
          section.replaceWith(replacement);
          bindFeedback(replacement);
          replacement.querySelector('textarea')?.focus({preventScroll: true});
        } catch (_) {
          if (error) {
            error.textContent = 'Feedback could not be confirmed. Reopen this conversation to check before sending again.';
            error.hidden = false;
          }
        } finally {
          feedbackSubmitting -= 1;
          delete section.dataset.submitting;
          if (draft) draft.readOnly = false;
          section.querySelectorAll('button').forEach(button => { button.disabled = false; });
        }
      });
    });
  }
  document.querySelectorAll('.answer-feedback').forEach(bindFeedback);
  function feedbackInUse() {
    return feedbackSubmitting > 0 || !!document.activeElement?.closest('.answer-feedback') ||
      [...document.querySelectorAll('.feedback-form textarea')].some(input => input.value.length > 0);
  }
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
    const settingsDialog = askForm.querySelector('.run-settings-dialog');
    let billingSaving = false;
    let authorizations = {};
    let authorizeSubmission = () => true;
    let refreshAuthorization = () => {};
    if (settingsDialog) {
    const settingsOpen = askForm.querySelector('.run-settings-open');
    const backend = askForm.querySelector('#run-backend');
    const processing = askForm.querySelector('#api-processing');
    const billingPanel = askForm.querySelector('.billing-authorization');
    const billingToggle = billingPanel.querySelector('.billing-toggle');
    const billingStatus = billingPanel.querySelector('.billing-status');
    const billingError = billingPanel.querySelector('.billing-error');
    const billingNote = billingPanel.querySelector('.settings-note');
    const billingHelp = billingNote.textContent;
    const microphone = askForm.querySelector('.dictation-toggle');
    authorizations = JSON.parse(settingsDialog.dataset.billingAuthorizations);
    const profiles = JSON.parse(settingsDialog.dataset.modelProfiles);
    let previousBackend = backend.value;
    const firstPartyProfile = {
      research_model: previousBackend === 'openrouter' ? 'gpt-6.1-terra' : askForm.querySelector('#research-model').value,
      answer_model: previousBackend === 'openrouter' ? 'gpt-6.1-sol' : askForm.querySelector('#answer-model').value,
      research_reasoning: askForm.querySelector('#research-reasoning').value,
      answer_reasoning: askForm.querySelector('#answer-reasoning').value,
      api_processing: processing.value
    };
    const profileFields = ['research_model', 'answer_model', 'research_reasoning', 'answer_reasoning'];
    function rememberProfile() {
      const profile = {};
      profileFields.forEach(name => { profile[name] = askForm.elements[name].value; });
      if (previousBackend === 'openai') profile.api_processing = processing.value;
      profiles[previousBackend] = profile;
    }
    function restoreProfile() {
      const profile = profiles[backend.value] || (backend.value === 'openrouter' ? {
        research_model: '', answer_model: '',
        research_reasoning: firstPartyProfile.research_reasoning,
        answer_reasoning: firstPartyProfile.answer_reasoning
      } : firstPartyProfile);
      profileFields.forEach(name => { askForm.elements[name].value = profile[name] || ''; });
      if (backend.value === 'openai' && profile.api_processing !== undefined) processing.value = profile.api_processing;
    }
    const billedBackend = () => backend.value === 'chatgpt_plan' ? 'openai' : backend.value;
    function updateAuthorization() {
      const plan = backend.value === 'chatgpt_plan';
      billingPanel.hidden = plan && microphone.dataset.configured !== 'true';
      billingNote.textContent = plan
        ? 'Dictation uses the separately billed OpenAI API. This authorization keeps the ChatGPT personal plan selected for research.'
        : billingHelp;
      const label = billedBackend() === 'openrouter' ? 'OpenRouter' : 'OpenAI API';
      const authorized = authorizations[billedBackend()] === true;
      if (microphone.dataset.configured === 'true') {
        microphone.dataset.enabled = String(authorizations.openai === true);
      }
      billingStatus.textContent = authorized ? label + ' billed inference is authorized.' : label + ' billed inference is not authorized.';
      billingToggle.textContent = (authorized ? 'Revoke ' : 'Authorize ') + label + ' billed inference';
    }
    const disclosures = {
      chatgpt_plan: 'Your question, conversation context, source text, PDFs and images used in this run are supplied through your ChatGPT personal plan.',
      openai: 'API billed. Your question, conversation context, source text, PDFs and images used in this run are supplied to OpenAI through its API.',
      openrouter: 'OpenRouter billed. OpenRouter can route your question, conversation context, source text, PDFs and images used in this run to underlying model providers.'
    };
    const backendLabels = {chatgpt_plan: 'ChatGPT plan', openai: 'OpenAI API · API billed', openrouter: 'OpenRouter · OpenRouter billed'};
    function updateRunSummary() {
      const effort = role => askForm.querySelector('#' + role + '-reasoning').value || 'model default';
      const model = role => askForm.querySelector('#' + role + '-model').value || 'choose model';
      settingsOpen.querySelector('.run-selection-backend').textContent = backendLabels[backend.value];
      settingsOpen.querySelector('.run-selection-roles').textContent = 'Research ' + model('research') + ' · ' + effort('research') + ' / Answer ' + model('answer') + ' · ' + effort('answer') + (backend.value === 'openai' ? ' · ' + (processing.value === 'fast' ? 'Fast' : processing.value === 'standard' ? 'Standard' : 'Choose processing') : '');
    }
    function updateBackend() {
      const api = backend.value === 'openai';
      askForm.querySelector('.run-processing').hidden = !api;
      processing.disabled = !api;
      processing.required = api;
      updateAuthorization();
      askForm.querySelector('#provider-disclosure').textContent = disclosures[backend.value];
      askForm.querySelector('.openrouter-model-help').hidden = backend.value !== 'openrouter';
      for (const role of ['research', 'answer']) {
        const input = askForm.querySelector('#' + role + '-model');
        input.placeholder = backend.value === 'openrouter' ? 'provider/model (exact identifier)' : 'Exact model identifier';
        const suggestions = askForm.querySelector('#' + role + '-suggestions');
        suggestions.replaceChildren(...['', 'gpt-6.1-terra', 'gpt-6.1-sol', 'gpt-6-luna'].map(model => {
          const option = document.createElement('option');
          option.value = model ? (backend.value === 'openrouter' ? 'openai/' : '') + model : '';
          option.textContent = option.value || 'Choose a suggestion…';
          return option;
        }));
      }
      updateRunSummary();
    }
    function openSettings() {
      if (!settingsDialog.open) settingsDialog.showModal();
    }
    function closeSettings() {
      settingsDialog.close();
      updateRunSummary();
      settingsOpen.focus({preventScroll: true});
    }
    settingsOpen.addEventListener('click', openSettings);
    settingsDialog.querySelector('.run-settings-close').addEventListener('click', closeSettings);
    settingsDialog.querySelector('.run-settings-done').addEventListener('click', () => {
      const invalid = [...settingsDialog.querySelectorAll('input, select')].find(control => !control.checkValidity());
      if (invalid) { invalid.reportValidity(); return; }
      closeSettings();
    });
    settingsDialog.addEventListener('cancel', () => updateRunSummary());
    settingsDialog.addEventListener('input', updateRunSummary);
    processing.addEventListener('change', () => {
      const inherited = askForm.querySelector('.initial-tier-profile');
      if (inherited) inherited.hidden = Boolean(processing.value);
    });
    backend.addEventListener('change', () => {
      rememberProfile();
      restoreProfile();
      previousBackend = backend.value;
      billingError.hidden = true;
      updateBackend();
    });
    askForm.querySelectorAll('.model-suggestions').forEach(suggestions => {
      suggestions.addEventListener('change', () => {
        if (!suggestions.value) return;
        const input = askForm.querySelector('#' + suggestions.dataset.role + '-model');
        input.value = suggestions.value;
        suggestions.value = '';
        updateRunSummary();
      });
    });
    billingToggle.addEventListener('click', async () => {
      const selectedBackend = billedBackend();
      billingSaving = true;
      billingToggle.disabled = true;
      backend.disabled = true;
      billingError.hidden = true;
      try {
        const response = await fetch(settingsDialog.dataset.billingUrl, {
          method: 'POST', credentials: 'same-origin', headers: {'Accept': 'application/json'},
          body: new URLSearchParams({form_token: settingsDialog.dataset.billingToken,
            backend: selectedBackend, authorized: authorizations[selectedBackend] ? '0' : '1'})
        });
        const result = await response.json().catch(() => null);
        if (result?.form_token) settingsDialog.dataset.billingToken = result.form_token;
        if (!response.ok || !result?.billing_authorizations) throw new Error('authorization_save_failed');
        authorizations = result.billing_authorizations;
        updateAuthorization();
      } catch (_) {
        billingError.textContent = 'Authorization could not be saved. Reopen Reading Room and try again.';
        billingError.hidden = false;
      } finally {
        billingSaving = false;
        billingToggle.disabled = false;
        backend.disabled = false;
      }
    });
    askForm.addEventListener('invalid', event => {
      if (settingsDialog.contains(event.target)) {
        openSettings();
        event.target.focus();
      }
    }, true);
    updateBackend();
    authorizeSubmission = () => {
      if (backend.value !== 'chatgpt_plan' && authorizations[backend.value] !== true) {
        openSettings();
        billingToggle.focus();
        return false;
      }
      return true;
    };
    refreshAuthorization = billing => {
      if (billing?.dataset.billingAuthorizations) {
        authorizations = JSON.parse(billing.dataset.billingAuthorizations);
        settingsDialog.dataset.billingToken = billing.dataset.billingToken;
        updateAuthorization();
      }
    };
    }
    const draftKey = 'scryraven-draft:' + askForm.dataset.draftKey;
    let submitting = false;
    let files = [];
    let objectURLs = [];
    let dragDepth = 0;
    let uploadProblem = '';
    const activeJob = ['queued', 'researching'].includes(document.body.dataset.jobState);
    const narrowComposer = matchMedia('(max-width: 760px)');
    const touchKeyboard = matchMedia('(pointer: coarse)');
    const visualViewport = window.visualViewport;
    function expand() {
      const height = narrowComposer.matches && visualViewport?.scale === 1
        ? visualViewport.height : innerHeight;
      question.style.height = 'auto';
      question.style.height = Math.max(44, Math.min(question.scrollHeight, 240, height * .35)) + 'px';
      if (narrowComposer.matches && reader.contains(question) && document.activeElement === question) {
        // On a short keyboard viewport, scroll the welcome pane as the draft
        // grows. Panning the document would move the composer under the keyboard.
        const overflow = question.getBoundingClientRect().bottom + 8 - reader.getBoundingClientRect().bottom;
        if (overflow > 0) reader.scrollTop += overflow;
      }
    }
    function fitComposer() {
      const resized = narrowComposer.matches && visualViewport?.scale === 1;
      document.body.style.setProperty('--reading-height', resized ? visualViewport.height + 'px' : '');
      // Safari can pan the layout viewport while the software keyboard is up.
      document.body.style.setProperty('--reading-top', resized ? visualViewport.offsetTop + 'px' : '');
      expand();
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
    fitComposer();
    window.addEventListener('resize', fitComposer);
    visualViewport?.addEventListener('resize', fitComposer);
    visualViewport?.addEventListener('scroll', fitComposer);
    const newLanguage = document.querySelector('#citation-language[form="ask-question"]');
    const languageKey = draftKey + ':source-language';
    if (newLanguage) {
      try {
        const previous = sessionStorage.getItem(languageKey);
        if ([...newLanguage.options].some(option => option.value === previous)) newLanguage.value = previous;
      } catch (_) {}
      newLanguage.addEventListener('change', () => {
        try { sessionStorage.setItem(languageKey, newLanguage.value); } catch (_) {}
      });
    }
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
      if (submitting || activeJob || billingSaving) return;
      if (uploadProblem) { showError(uploadProblem); return; }
      if (!question.value.trim()) {
        question.setCustomValidity('Write a research question to begin.');
        question.reportValidity();
        return;
      }
      if (!askForm.reportValidity()) return;
      if (!authorizeSubmission()) return;
      submitting = true;
      submit.disabled = true;
      question.readOnly = true;
      picker.disabled = true;
      askForm.setAttribute('aria-busy', 'true');
      announcement.textContent = 'Submitting your question and attachments.';
      showError('');
      recovery.hidden = true;
      recovery.replaceChildren();
      // Snapshot every file with the question before disabling picker controls.
      const body = new FormData(askForm);
      body.delete('files');
      files.forEach(file => body.append('files', file, file.name));
      try {
        const response = await fetch(askForm.action, {method: 'POST', body, credentials: 'same-origin'});
        if (!response.ok) {
          const rendered = new DOMParser().parseFromString(await response.text(), 'text/html');
          showError(rendered.querySelector('.error-notice')?.textContent.trim() || 'Your question could not be accepted. Your text and selected files are still here.');
          const billing = rendered.querySelector('.run-settings-dialog');
          refreshAuthorization(billing);
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
        try {
          sessionStorage.removeItem(draftKey);
          if (newLanguage) sessionStorage.removeItem(languageKey);
        } catch (_) {}
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
    let composing = false;
    question.addEventListener('compositionstart', () => { composing = true; });
    question.addEventListener('compositionend', () => { composing = false; });
    question.addEventListener('keydown', event => {
      if (event.key !== 'Enter' || event.shiftKey || event.altKey ||
          composing || event.isComposing || event.keyCode === 229) return;
      if (touchKeyboard.matches && !event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      if (!event.repeat && !submit.disabled) askForm.requestSubmit(submit);
    });
    window.addEventListener('pagehide', saveDraft);
    window.addEventListener('pageshow', () => {
      submitting = false;
      submit.disabled = activeJob;
      question.readOnly = false;
      picker.disabled = false;
      askForm.removeAttribute('aria-busy');
      fitComposer();
    });
  }

  const stateLabels = {queued: 'Queued', researching: 'Researching', failed: 'Failed', interrupted: 'Interrupted'};
  const knownJobs = new Map();
  const sessionRows = new Map();
  document.querySelectorAll('.session-row[data-session-id]').forEach(row => {
    sessionRows.set(row.dataset.sessionId, row);
    const {jobId, state} = row.querySelector('.session-job-state').dataset;
    knownJobs.set(row.dataset.sessionId, {jobId, state});
    row.querySelector('.session-link').addEventListener('click', openUnrenderedAnswer);
  });
  const notifications = document.querySelector('.research-notifications');
  const visibleAnswers = new Set();
  const acknowledging = new Set();
  const completionObserver = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (entry.intersectionRatio > 0) visibleAnswers.add(entry.target);
      else visibleAnswers.delete(entry.target);
    }
    acknowledgeVisibleAnswers();
  }, {threshold: 0.01});
  document.querySelectorAll('[data-completion-url]').forEach(answer => completionObserver.observe(answer));

  function acknowledgeVisibleAnswers() {
    if (document.hidden || document.querySelector('.workspace[inert], dialog[open]')) return;
    for (const answer of visibleAnswers) {
      if (!acknowledging.has(answer)) acknowledgeAnswer(answer);
    }
  }

  async function acknowledgeAnswer(answer) {
    acknowledging.add(answer);
    try {
      const response = await fetch(answer.dataset.completionUrl, {
        method: 'POST', credentials: 'same-origin', keepalive: true,
        body: new URLSearchParams({form_token: answer.dataset.completionToken}),
      });
      if (response.status === 204) {
        completionObserver.unobserve(answer);
        visibleAnswers.delete(answer);
        pollJobs();
      }
    } catch (_) { /* An interrupted acknowledgment can safely be retried. */ }
    finally { acknowledging.delete(answer); }
  }

  function refreshVisibleJobs() {
    if (!document.hidden) pollJobs();
  }
  document.addEventListener('visibilitychange', refreshVisibleJobs);
  window.addEventListener('pageshow', refreshVisibleJobs);

  function openUnrenderedAnswer(event) {
    const link = event.currentTarget;
    if (event.defaultPrevented || event.button !== 0 || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey ||
        link.pathname !== location.pathname || !link.hash.startsWith('#turn-') ||
        document.getElementById(link.hash.slice(1))) return;
    // The answer finished after this document rendered. A fragment alone cannot load it.
    event.preventDefault();
    saveDraft();
    history.replaceState(null, '', link.href);
    location.reload();
  }

  function updateJobBadges(job) {
    const row = sessionRows.get(job.session_id);
    if (row) {
      const badge = row.querySelector('.session-job-state');
      badge.dataset.state = job.state;
      badge.dataset.jobId = job.job_id;
      badge.textContent = stateLabels[job.state] || '';
      badge.hidden = !stateLabels[job.state];
      const completion = row.querySelector('.session-completion-state');
      completion.dataset.jobId = job.new_answer?.job_id || '';
      completion.hidden = !job.new_answer;
      row.querySelector('.session-link').hash = job.new_answer ? 'turn-' + job.new_answer.turn : '';
    }
    if (notifications.dataset.sessionId === job.session_id && notifications.dataset.state === 'completed' &&
        notifications.dataset.jobId !== job.new_answer?.job_id) {
      notifications.replaceChildren();
      delete notifications.dataset.jobId;
    }
  }

  function notifyJob(job) {
    if (job.state === 'completed' && job.new_answer?.job_id !== job.job_id) return;
    if (notifications.dataset.jobId === job.job_id && notifications.dataset.state === job.state) return;
    notifications.replaceChildren();
    notifications.dataset.state = job.state;
    notifications.dataset.jobId = job.job_id;
    notifications.dataset.sessionId = job.session_id;
    const message = document.createElement('span');
    message.textContent = job.state === 'completed' ? 'Research completed. ' : 'Research ' + stateLabels[job.state].toLowerCase() + '. ';
    const link = document.createElement('a');
    link.href = '/sessions/' + encodeURIComponent(job.session_id);
    if (job.state === 'completed') {
      link.hash = 'turn-' + (job.revision + 1);
      link.addEventListener('click', openUnrenderedAnswer);
    }
    link.textContent = 'Open conversation';
    notifications.append(message, link);
  }
  let pollTimer;
  let polling = false;
  async function pollJobs() {
    if (polling) return;
    polling = true;
    clearTimeout(pollTimer);
    acknowledgeVisibleAnswers();
    try {
      const response = await fetch('/jobs/status', {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
      if (response.ok) {
        const status = await response.json();
        for (const job of status.jobs || []) {
          const previous = knownJobs.get(job.session_id);
          knownJobs.set(job.session_id, {jobId: job.job_id, state: job.state});
          updateJobBadges(job);
          const isCurrent = job.session_id === document.body.dataset.sessionId && job.job_id === document.body.dataset.jobId;
          if (isCurrent && ['queued', 'researching'].includes(document.body.dataset.jobState)) {
            if (['completed', 'failed', 'interrupted'].includes(job.state)) {
              if (feedbackInUse() || askForm?.querySelector('.dictation-toggle[aria-busy="true"]')) {
                notifyJob(job);
                continue;
              }
              saveDraft();
              if (job.state === 'completed') history.replaceState(null, '', '#turn-' + (job.revision + 1));
              location.reload();
              return;
            }
            if (job.state === 'researching') {
              const message = document.querySelector('.research-job .job-message');
              if (message) {
                message.querySelector('strong').textContent = 'Researching';
                message.querySelector('p').textContent = 'ScryRaven is working on your question. You may navigate away while research continues.';
              }
              document.body.dataset.jobState = 'researching';
            }
          } else if ((job.state === 'completed' && (previous?.state !== 'completed' || previous.jobId !== job.job_id)) ||
                     (['queued', 'researching'].includes(previous?.state) && ['failed', 'interrupted'].includes(job.state))) {
            notifyJob(job);
          }
        }
      }
    } catch (_) { /* A disconnected browser does not determine the job state. */ }
    finally {
      polling = false;
      pollTimer = setTimeout(pollJobs, document.hidden ? 4000 : 1500);
    }
  }
  if (document.querySelector('.history-list')) pollJobs();

  const sidebar = document.querySelector('.sidebar');
  const workspace = document.querySelector('.workspace');
  const openHistory = document.querySelector('.open-history');
  const historyBackdrop = document.querySelector('.history-backdrop');
  function closeHistory(restoreFocus = true) {
    closeActionMenus();
    sidebar.classList.remove('is-open');
    sidebar.removeAttribute('role');
    sidebar.removeAttribute('aria-modal');
    workspace.inert = false;
    historyBackdrop.hidden = true;
    if (location.hash === '#history') history.replaceState(null, '', location.pathname + location.search);
    if (restoreFocus) openHistory.focus({preventScroll: true});
  }
  function showHistory() {
    sidebar.classList.add('is-open');
    sidebar.setAttribute('role', 'dialog');
    sidebar.setAttribute('aria-modal', 'true');
    historyBackdrop.hidden = false;
    workspace.inert = true;
    sidebar.querySelector('.close-history').focus();
  }
  openHistory.addEventListener('click', event => {
    event.preventDefault();
    showHistory();
  });
  sidebar.querySelector('.close-history').addEventListener('click', event => { event.preventDefault(); closeHistory(); });
  historyBackdrop.addEventListener('click', () => closeHistory());
  sidebar.addEventListener('keydown', event => {
    if (!sidebar.classList.contains('is-open') || event.key !== 'Tab') return;
    const focusable = [...sidebar.querySelectorAll('a, summary, button')].filter(el => el.getClientRects().length);
    const first = focusable[0], last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  narrow.addEventListener('change', () => {
    if (sidebar.classList.contains('is-open')) closeHistory();
  });
  function adoptHistoryFragment() {
    if (!narrow.matches) return;
    if (location.hash === '#history') showHistory();
    else if (sidebar.classList.contains('is-open')) closeHistory(false);
  }
  sidebar.setAttribute('data-history-enhanced', '');
  adoptHistoryFragment();
  window.addEventListener('hashchange', adoptHistoryFragment);

  document.querySelectorAll('[data-dialog-open]').forEach(button => {
    const dialog = document.getElementById(button.dataset.dialogOpen);
    if (!dialog) return;
    button.addEventListener('click', () => {
      if (sidebar.classList.contains('is-open')) closeHistory(false);
      dialog.showModal();
      dialog.dataset.returnToHistory = String(narrow.matches && sidebar.contains(button));
      dialog.addEventListener('close', () => {
        if (dialog.dataset.returnToHistory === 'true') openHistory.focus({preventScroll: true});
        else button.focus({preventScroll: true});
      }, {once: true});
    });
    button.disabled = false;
  });
  document.querySelectorAll('[data-dialog-close]').forEach(button => {
    button.addEventListener('click', () => button.closest('dialog').close());
  });
  const sourceSettings = document.querySelector('form.source-settings');
  if (sourceSettings) {
    const save = sourceSettings.querySelector('button[type=submit]');
    const status = sourceSettings.querySelector('[role=status]');
    const language = sourceSettings.elements.citation_language;
    sourceSettings.addEventListener('submit', async event => {
      event.preventDefault();
      if (save.disabled) return;
      const body = new URLSearchParams(new FormData(sourceSettings));
      save.disabled = language.disabled = true;
      status.textContent = 'Saving…';
      try {
        const response = await fetch(sourceSettings.action, {
          method: 'POST', credentials: 'same-origin', headers: {Accept: 'application/json'}, body
        });
        if (!response.ok) throw new Error('source_language_save_failed');
        sourceSettings.elements.form_token.value = (await response.json()).form_token;
        status.textContent = 'Language saved.';
      } catch (_) {
        status.textContent = 'Language could not be saved. Reopen Settings after refreshing the conversation.';
      } finally {
        save.disabled = language.disabled = false;
      }
    });
    language.addEventListener('change', () => { status.textContent = ''; });
  }
  const hostedSettings = document.querySelector('#hosted-settings-dialog');
  if (hostedSettings) {
    const choices = JSON.parse(hostedSettings.dataset.modelChoices);
    hostedSettings.querySelectorAll('[data-hosted-role]').forEach(model => {
      model.addEventListener('change', () => {
        const reasoning = hostedSettings.querySelector('[name=' + model.dataset.hostedRole + '_reasoning]');
        const previous = reasoning.value;
        const efforts = choices[model.value].reasoning;
        reasoning.replaceChildren(...efforts.map(effort => new Option(effort ? effort[0].toUpperCase() + effort.slice(1) : 'Model default', effort)));
        reasoning.value = efforts.includes(previous) ? previous : efforts.includes('medium') ? 'medium' : efforts[0];
      });
    });
  }

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
    // A modal owns Escape. Native dismissal must leave the underlying editor,
    // history drawer and conversation in place.
    if (event.defaultPrevented || event.target.closest('dialog[open]')) return;
    if (!preview.hidden) { event.preventDefault(); closePreview(true); return; }
    if (document.querySelector('.session-actions[open]')) { event.preventDefault(); closeActionMenus(true); return; }
    if (sidebar.classList.contains('is-open')) { closeHistory(); return; }
    if (rename) { location.href = rename.querySelector('.rename-cancel').href; return; }
    document.querySelectorAll('.session-actions[open]').forEach(menu => {
      menu.open = false;
      menu.querySelector('summary').focus();
    });
  });
})();
