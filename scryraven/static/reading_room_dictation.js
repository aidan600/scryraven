(() => {
  'use strict';
  const button = document.querySelector('.dictation-toggle');
  if (!button) return;
  const form = button.closest('form');
  const question = form.querySelector('#question');
  const submit = form.querySelector('.submit-question');
  const controls = form.querySelector('.dictation-controls');
  const status = controls.querySelector('.dictation-status');
  const cancel = controls.querySelector('.dictation-cancel');
  const maxSeconds = Number(button.dataset.maxSeconds);
  const targetRate = 16000;
  let recording = null;

  function display(message, state = '') {
    const active = state === 'recording';
    const ready = state === 'ready';
    status.textContent = message;
    controls.hidden = !message;
    cancel.hidden = !state;
    button.disabled = Boolean(state && !active && !ready);
    button.setAttribute('aria-busy', String(Boolean(state)));
    submit.setAttribute('aria-disabled', String(Boolean(state) || submit.disabled));
    button.classList.toggle('is-recording', active);
    button.querySelector('.dictation-mic').hidden = active;
    button.querySelector('.dictation-stop').hidden = !active;
    const label = active ? 'Stop and transcribe' : ready ? 'Transcribe recording' : 'Start dictation';
    button.setAttribute('aria-label', label);
    button.title = state ? label : 'Dictate with OpenAI';
  }

  function releaseMicrophone(run) {
    run.stream?.getTracks().forEach(track => track.stop());
    if (run.node) {
      run.node.disconnect();
      run.node.port.close();
      run.node = null;
    }
    if (run.audio && run.audio.state !== 'closed') void run.audio.close().catch(() => {});
  }

  function finish(run, message) {
    if (recording !== run) return;
    recording = null;
    clearTimeout(run.timer);
    releaseMicrophone(run);
    run.abort.abort();
    run.chunks.length = 0;
    display(message);
  }

  async function encodeWav(run) {
    const frameCount = Math.min(run.frames, Math.floor(run.rate * maxSeconds));
    const length = Math.floor(frameCount * targetRate / run.rate);
    if (length < targetRate / 4) return null;
    const resampler = new OfflineAudioContext(1, length, targetRate);
    const audio = resampler.createBuffer(1, frameCount, run.rate);
    const input = audio.getChannelData(0);
    let offset = 0;
    for (const chunk of run.chunks) {
      const samples = chunk.subarray(0, frameCount - offset);
      input.set(samples, offset);
      offset += samples.length;
      if (offset === frameCount) break;
    }
    run.chunks.length = 0;
    const source = resampler.createBufferSource();
    source.buffer = audio;
    source.connect(resampler.destination);
    source.start();
    const output = (await resampler.startRendering()).getChannelData(0);
    const bytes = new ArrayBuffer(44 + length * 2);
    const wav = new DataView(bytes);
    for (const [index, label] of [[0, 'RIFF'], [8, 'WAVEfmt '], [36, 'data']]) {
      for (let i = 0; i < label.length; i++) wav.setUint8(index + i, label.charCodeAt(i));
    }
    wav.setUint32(4, bytes.byteLength - 8, true);
    wav.setUint32(16, 16, true);          // PCM format chunk length
    wav.setUint16(20, 1, true);           // PCM
    wav.setUint16(22, 1, true);           // Mono
    wav.setUint32(24, targetRate, true);
    wav.setUint32(28, targetRate * 2, true);
    wav.setUint16(32, 2, true);           // Bytes per frame
    wav.setUint16(34, 16, true);          // Bits per sample
    wav.setUint32(40, length * 2, true);
    for (let i = 0; i < output.length; i++) {
      const sample = Math.max(-1, Math.min(1, output[i]));
      wav.setInt16(44 + i * 2, sample * (sample < 0 ? 32768 : 32767), true);
    }
    return bytes;
  }

  async function transcribe(run) {
    clearTimeout(run.timer);
    releaseMicrophone(run);
    display('Transcribing with OpenAI…', 'transcribing');
    run.timer = setTimeout(() => finish(run, 'Dictation timed out. Try again.'), 45000);
    try {
      const body = await encodeWav(run);
      if (recording !== run) return;
      if (!body) {
        finish(run, 'That recording was too short. Try speaking for a little longer.');
        return;
      }
      const response = await fetch(button.dataset.url, {
        method: 'POST', credentials: 'same-origin', signal: run.abort.signal,
        headers: {'Content-Type': 'audio/wav', 'Accept': 'application/json', 'X-Form-Token': button.dataset.token},
        body
      });
      const result = await response.json().catch(() => null);
      if (recording !== run) return;
      if (!response.ok) {
        finish(run, result?.error || 'Dictation could not be transcribed. Try again.');
        return;
      }
      const text = typeof result?.text === 'string' ? result.text.trim() : '';
      if (!text) {
        finish(run, 'No speech was transcribed. Try again.');
        return;
      }
      const separator = question.value && !/\s$/.test(question.value) ? ' ' : '';
      if (question.value.length + separator.length + text.length > 20000) {
        finish(run, 'The transcript would exceed the 20,000-character question limit.');
        return;
      }
      question.value += separator + text;
      question.dispatchEvent(new Event('input', {bubbles: true}));
      finish(run, 'Transcript added to your draft.');
    } catch (_) {
      finish(run, 'Dictation could not be completed. Try again.');
    }
  }

  function stop(run, transcribeNow = false) {
    if (run.phase !== 'recording') return;
    run.phase = 'finishing';
    run.transcribeNow = transcribeNow;
    clearTimeout(run.timer);
    display('Preparing your recording…', 'finishing');
    run.stream.getTracks().forEach(track => track.stop());
    run.node.port.postMessage('stop');
    run.timer = setTimeout(() => finish(run, 'Recording was interrupted. Try again.'), 2000);
  }

  async function start() {
    if (button.dataset.enabled !== 'true') {
      const message = button.dataset.unavailable || 'Authorize OpenAI API billing in Run settings to use dictation.';
      display(message);
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext ||
        !window.AudioWorkletNode || !window.OfflineAudioContext) {
      display('Microphone recording is unavailable in this browser.');
      return;
    }
    const run = {phase: 'starting', abort: new AbortController(), chunks: [], frames: 0};
    recording = run;
    display('Waiting for the microphone…', 'starting');
    run.timer = setTimeout(() => finish(run, 'Microphone access timed out. Try again.'), 20000);
    try {
      run.audio = new AudioContext();
      const resumed = run.audio.resume();
      const microphone = navigator.mediaDevices.getUserMedia({audio: true}).then(stream => {
        if (recording !== run) stream.getTracks().forEach(track => track.stop());
        else run.stream = stream;
      });
      await Promise.all([resumed, microphone, run.audio.audioWorklet.addModule(button.dataset.worklet)]);
      if (recording !== run) return;
      run.rate = run.audio.sampleRate;
      run.node = new AudioWorkletNode(run.audio, 'dictation-recorder', {
        channelCount: 1, channelCountMode: 'explicit'
      });
      run.node.port.onmessage = ({data}) => {
        if (recording !== run) return;
        if (data === 'stopped') {
          if (run.transcribeNow) void transcribe(run);
          else {
            clearTimeout(run.timer);
            releaseMicrophone(run);
            run.phase = 'ready';
            display('Recording limit reached. Transcribe or cancel.', 'ready');
            run.timer = setTimeout(() => finish(run, 'Recording expired. Try again.'), 60000);
          }
          return;
        }
        if (run.frames < run.rate * maxSeconds) {
          run.chunks.push(data);
          run.frames += data.length;
          if (run.frames >= run.rate * maxSeconds) stop(run);
        }
      };
      run.stream.getAudioTracks().forEach(track => track.addEventListener('ended', () => {
        if (run.phase === 'recording') finish(run, 'Microphone recording was interrupted. Try again.');
      }));
      run.audio.createMediaStreamSource(run.stream).connect(run.node);
      run.node.connect(run.audio.destination);
      run.phase = 'recording';
      clearTimeout(run.timer);
      run.timer = setTimeout(() => stop(run), maxSeconds * 1000);
      display('Recording… Stop to transcribe with OpenAI.', 'recording');
    } catch (error) {
      finish(run, error.name === 'NotAllowedError' || error.name === 'SecurityError'
        ? 'Microphone permission was denied. Allow access in your browser to dictate.'
        : 'Microphone recording could not start. Check your microphone and try again.');
    }
  }

  button.hidden = false;
  button.addEventListener('click', () => {
    if (form.getAttribute('aria-busy') === 'true') return;
    if (recording?.phase === 'ready') void transcribe(recording);
    else if (recording) stop(recording, true);
    else void start();
  });
  cancel.addEventListener('click', () => {
    if (recording) finish(recording, 'Dictation canceled.');
    button.focus({preventScroll: true});
  });
  form.addEventListener('submit', event => {
    if (!recording) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    status.textContent = 'Finish or cancel dictation before sending.';
  }, true);
  window.addEventListener('pagehide', () => {
    if (recording) finish(recording, '');
  });
})();
