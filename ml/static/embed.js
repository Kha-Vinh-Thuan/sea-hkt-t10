/* T10 Interview AI web component: drop the interview room into any internal page.

  <script src="https://<t10-host>/embed.js"></script>
  <t10-interview token="EMBED_TOKEN_FROM_POST_/v1/sessions"></t10-interview>

The room runs in an iframe served by T10 (camera, mic and fullscreen delegated with `allow`), so the host page never
touches the candidate's media. Events bubble out as DOM events: t10:ready, t10:done.
*/
(() => {
  const origin = new URL(document.currentScript.src).origin;
  class T10Interview extends HTMLElement {
    connectedCallback() {
      const token = this.getAttribute('token');
      if (!token) { this.textContent = 't10-interview: missing token attribute'; return; }
      const frame = document.createElement('iframe');
      frame.src = `${origin}/join/${encodeURIComponent(token)}`;
      frame.allow = 'camera; microphone; fullscreen; display-capture';
      frame.allowFullscreen = true;
      frame.title = 'Phỏng vấn trực tuyến';
      frame.style.cssText = 'width:100%;min-height:640px;border:0;border-radius:12px;';
      this.replaceChildren(frame);
      window.addEventListener('message', (e) => {
        if (e.origin !== origin || e.source !== frame.contentWindow || !e.data || !e.data.t10) return;
        this.dispatchEvent(new CustomEvent(`t10:${e.data.t10}`, {detail: e.data, bubbles: true}));
      });
    }
  }
  if (!customElements.get('t10-interview')) customElements.define('t10-interview', T10Interview);
})();
