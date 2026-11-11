class DictationRecorder extends AudioWorkletProcessor {
  constructor() {
    super();
    this.samples = new Float32Array(2048);
    this.used = 0;
    this.stopped = false;
    this.port.onmessage = () => {
      this.stopped = true;
      this.flush();
      this.port.postMessage('stopped');
    };
  }

  flush() {
    if (!this.used) return;
    const chunk = this.used === this.samples.length ? this.samples : this.samples.slice(0, this.used);
    this.port.postMessage(chunk, [chunk.buffer]);
    this.samples = new Float32Array(2048);
    this.used = 0;
  }

  process(inputs) {
    if (this.stopped) return false;
    const channel = inputs[0][0];
    if (channel) {
      for (const sample of channel) {
        this.samples[this.used++] = sample;
        if (this.used === this.samples.length) this.flush();
      }
    }
    // The processor has no audible output.
    return true;
  }
}

registerProcessor('dictation-recorder', DictationRecorder);
