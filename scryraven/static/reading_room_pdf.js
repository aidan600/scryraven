(() => {
  const standalone = navigator.standalone === true || matchMedia('(display-mode: standalone)').matches;
  if (!standalone) {
    document.querySelectorAll('.browser-pdf-download').forEach(link => { link.hidden = false; });
    return;
  }

  const dialog = document.querySelector('#answer-pdf-dialog');
  if (!dialog?.showModal) return;
  const status = dialog.querySelector('.pdf-download-status');
  const retry = dialog.querySelector('.pdf-download-retry');
  const share = dialog.querySelector('.pdf-download-share');
  const save = dialog.querySelector('.pdf-download-save');
  const safari = dialog.querySelector('.pdf-download-safari');
  const pageAddress = safari.querySelector('input');
  const supportsDownload = 'download' in save && typeof URL.createObjectURL === 'function';
  let current = null;

  function release() {
    current?.controller?.abort();
    if (current?.url) URL.revokeObjectURL(current.url);
    save.removeAttribute('href');
    current = null;
  }

  function fileToShare(blob, filename) {
    if (typeof File !== 'function' || typeof navigator.share !== 'function' ||
        typeof navigator.canShare !== 'function') return null;
    try {
      const data = {files: [new File([blob], filename, {type: 'application/pdf'})]};
      return navigator.canShare(data) ? data : null;
    } catch {
      return null;
    }
  }

  async function prepare(download) {
    if (download.controller) return;
    const controller = new AbortController();
    download.controller = controller;
    status.textContent = 'Preparing PDF…';
    retry.hidden = share.hidden = save.hidden = safari.hidden = true;
    try {
      const response = await fetch(download.opener.dataset.pdfUrl, {
        credentials: 'same-origin',
        mode: 'same-origin',
        cache: 'no-store',
        redirect: 'error',
        signal: controller.signal,
      });
      if (!response.ok || response.headers.get('Content-Type')?.split(';')[0] !== 'application/pdf') {
        throw new Error('PDF unavailable');
      }
      const blob = await response.blob();
      if (current !== download || !dialog.open) return;
      if (!blob.size) throw new Error('Empty PDF');
      const filename = download.opener.dataset.pdfFilename;
      download.shareData = fileToShare(blob, filename);
      share.hidden = !download.shareData;
      share.disabled = false;
      if (supportsDownload) {
        download.url = URL.createObjectURL(blob);
        save.download = filename;
        save.href = download.url;
        save.hidden = false;
      }
      safari.hidden = Boolean(download.shareData);
      if (download.shareData) status.textContent = 'Choose Share PDF, then Save to Files.';
      else if (supportsDownload) status.textContent = 'Use Save PDF to download the file.';
      else status.textContent = 'Open this answer in Safari to download the PDF.';
    } catch {
      if (current !== download || !dialog.open) return;
      status.textContent = 'Could not prepare the PDF. You can retry or close.';
      retry.hidden = false;
      safari.hidden = false;
    } finally {
      download.controller = null;
    }
  }

  document.querySelectorAll('.standalone-pdf-download').forEach(opener => {
    opener.hidden = false;
    opener.addEventListener('click', () => {
      if (dialog.open) return;
      release();
      current = {opener};
      pageAddress.value = new URL(opener.dataset.pdfAnswerUrl, location.origin).href;
      safari.open = false;
      dialog.showModal();
      prepare(current);
    });
  });

  retry.addEventListener('click', () => { if (current) prepare(current); });
  share.addEventListener('click', async () => {
    const download = current;
    if (!download?.shareData || share.disabled) return;
    share.disabled = true;
    try {
      // This tap supplies activation. Preparing the file may have taken too long.
      await navigator.share(download.shareData);
      if (current === download && dialog.open) status.textContent = 'Sharing finished.';
    } catch (error) {
      if (current !== download || !dialog.open) return;
      if (error?.name === 'AbortError') {
        status.textContent = 'Sharing canceled. You can try again or close.';
      } else {
        status.textContent = 'Could not share the PDF. Try saving it or open this answer in Safari.';
      }
      safari.hidden = false;
    } finally {
      if (current === download) share.disabled = false;
    }
  });

  save.addEventListener('click', event => {
    if (event.defaultPrevented || !current?.url) return;
    status.textContent = 'If the download does not start, open this answer in Safari.';
    safari.hidden = false;
  });
  pageAddress.addEventListener('focus', () => pageAddress.select());
  dialog.addEventListener('close', () => {
    if (dialog.open) return;
    const opener = current?.opener;
    release();
    opener?.focus({preventScroll: true});
  });
  window.addEventListener('pagehide', () => {
    if (dialog.open) dialog.close();
    release();
  });
})();
