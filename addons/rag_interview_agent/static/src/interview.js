// Candidate page. Voice runs over WebRTC straight to OpenAI Realtime (speech-to-speech); Odoo's RAG agent decides
// every word the voice says. Realtime answers nothing on its own (create_response=false on the server side).
(() => {
    const token = location.pathname.split('/').pop();
    const $ = (id) => document.getElementById(id);
    const rpc = async (path, params = {}) => {
        const r = await fetch(`/rag-interview/${token}/${path}`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({jsonrpc: '2.0', method: 'call', params}),
        });
        const body = r.ok ? await r.json() : null;
        return (body && body.result) || {error: 'ai'};
    };
    const status = (text, mode = '') => { $('status').textContent = text; $('orb').className = 'orb ' + mode; };

    let pc, dc, answer = '', speaking = false, finished = false, busy = false;

    const say = (text) => new Promise((resolve) => {
        speaking = true; status('Đang nói...', 'talk');
        $('question').textContent = text;
        say.done = resolve;
        // Out-of-band instructions: the voice reads exactly this text, nothing is added to its own memory.
        dc.send(JSON.stringify({type: 'response.create', response: {
            conversation: 'none', output_modalities: ['audio'],
            instructions: `Đọc nguyên văn, giọng tự nhiên, không thêm bớt chữ nào:\n${text}`,
        }}));
    });
    // Audio keeps playing a moment after the response is generated: wait for the buffer to drain.
    const spoke = () => { speaking = false; dc.send(JSON.stringify({type: 'input_audio_buffer.clear'}));
                          if (say.done) { say.done(); say.done = null; } };

    const listen = () => {
        answer = ''; $('heard').textContent = '';
        status('Mời bạn trả lời, mình đang nghe...', 'listen');
        $('done').disabled = false;
    };

    const handle = async (res) => {
        if (res.error === 'closed') return end('Buổi phỏng vấn đã kết thúc.');
        if (res.error === 'busy') return;
        if (res.error) {
            await say('Xin lỗi, kết nối vừa bị gián đoạn. Bạn nói lại câu trả lời giúp mình nhé.');
            return listen();
        }
        await say(res.question);
        if (res.done) return end('Cảm ơn bạn! Buổi phỏng vấn đã kết thúc, bạn có thể đóng trang này.');
        listen();
    };

    const submit = async () => {
        const text = answer.trim();
        if (busy || speaking || finished || !text) return;
        busy = true; $('done').disabled = true;
        status('Đang suy nghĩ...');
        try { await handle(await rpc('answer', {text})); } finally { busy = false; }
    };
    $('done').addEventListener('click', submit);

    const onEvent = (e) => {
        const ev = JSON.parse(e.data);
        if (ev.type === 'output_audio_buffer.stopped' || ev.type === 'output_audio_buffer.cleared') spoke();
        else if (ev.type === 'conversation.item.input_audio_transcription.completed' && !speaking && !busy && !finished) {
            // server VAD closed a speech segment; one answer can span several segments, so pause-to-send is ours
            answer += (ev.transcript || '') + ' ';
            $('heard').textContent = answer.trim();
            clearTimeout(onEvent.t);
            onEvent.t = setTimeout(submit, 2500);
        } else if (ev.type === 'error') console.warn('realtime', ev.error);
    };

    const end = (text) => {
        finished = true; $('done').disabled = true; status(text);
        setTimeout(() => { if (pc) pc.close(); }, 1500);
    };

    $('agree').addEventListener('change', (e) => { $('start').disabled = !e.target.checked; });
    $('start').addEventListener('click', async () => {
        $('start').disabled = true; $('blocker').textContent = '';
        let mic;
        try { mic = await navigator.mediaDevices.getUserMedia({audio: true}); } catch {
            $('blocker').textContent = 'Cần cho phép micro để phỏng vấn.'; $('start').disabled = false; return;
        }
        const voice = await rpc('voice');
        if (voice.error) {
            $('blocker').textContent = voice.error === 'closed' ? 'Buổi phỏng vấn đã kết thúc.' : `Không kết nối được dịch vụ giọng nói: ${voice.detail || 'vui lòng thử lại.'}`;
            $('start').disabled = false; return;
        }
        pc = new RTCPeerConnection();
        const audio = new Audio(); audio.autoplay = true;
        pc.ontrack = (e) => { audio.srcObject = e.streams[0]; };
        pc.addTrack(mic.getTracks()[0]);
        dc = pc.createDataChannel('oai-events');
        dc.onmessage = onEvent;
        await pc.setLocalDescription(await pc.createOffer());
        const sdp = await fetch(`https://api.openai.com/v1/realtime/calls?model=${encodeURIComponent(voice.model)}`, {
            method: 'POST', body: pc.localDescription.sdp,
            headers: {Authorization: `Bearer ${voice.secret}`, 'Content-Type': 'application/sdp'},
        });
        if (!sdp.ok) { $('blocker').textContent = 'Không kết nối được dịch vụ giọng nói.'; $('start').disabled = false; return; }
        await pc.setRemoteDescription({type: 'answer', sdp: await sdp.text()});
        await new Promise((r) => (dc.readyState === 'open' ? r() : dc.addEventListener('open', r, {once: true})));
        $('consent').hidden = true; $('stage').hidden = false;
        status('Đang chuẩn bị câu hỏi...');
        busy = true;
        try { await handle(await rpc('start')); } finally { busy = false; }
    });
})();
