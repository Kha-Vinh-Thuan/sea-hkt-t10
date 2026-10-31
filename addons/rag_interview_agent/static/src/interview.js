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

    let pc, dc, micStream, speaking = false, finished = false, busy = false;
    const draft = $('answer-draft');
    const stageError = $('stage-error');
    const showError = (text) => { stageError.textContent = text; stageError.hidden = !text; };
    const updateSubmit = () => { $('done').disabled = busy || speaking || finished || !draft.value.trim(); };

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
        if (micStream) micStream.getAudioTracks().forEach(track => { track.enabled = true; });
        status('Đang nghe. Hãy kiểm tra bản nháp rồi bấm Gửi câu trả lời.', 'listen');
        draft.disabled = false;
        updateSubmit();
    };

    const handle = async (res) => {
        if (res.error === 'closed') return end('Buổi phỏng vấn đã kết thúc.');
        if (res.error === 'busy') {
            showError('Hệ thống đang xử lý câu trả lời. Vui lòng thử gửi lại sau ít giây.');
            status('Chưa gửi được. Bạn có thể thử lại.', 'listen');
            return false;
        }
        if (res.error) {
            showError('Chưa gửi được câu trả lời. Nội dung của bạn vẫn ở đây; vui lòng thử lại.');
            status('Chưa gửi được. Bạn có thể thử lại.', 'listen');
            return false;
        }
        showError('');
        if (res.done) { end('Cảm ơn bạn! Buổi phỏng vấn đã kết thúc, bạn có thể đóng trang này.'); return true; }
        await say(res.question);
        listen();
        return true;
    };

    const submit = async () => {
        const text = draft.value.trim();
        if (busy || speaking || finished || !text) return;
        busy = true; draft.disabled = true; updateSubmit();
        if (micStream) micStream.getAudioTracks().forEach(track => { track.enabled = false; });
        status('Đang gửi câu trả lời...');
        try {
            const res = await rpc('answer', {text});
            if (!res.error) draft.value = '';
            await handle(res);
        } catch {
            showError('Kết nối bị gián đoạn. Nội dung của bạn vẫn ở đây; vui lòng thử lại.');
            status('Kết nối gián đoạn. Bạn có thể thử lại.', 'listen');
        } finally {
            busy = false;
            if (!finished) {
                if (!speaking && micStream) micStream.getAudioTracks().forEach(track => { track.enabled = true; });
                draft.disabled = false; updateSubmit();
            }
        }
    };
    $('done').addEventListener('click', submit);
    draft.addEventListener('input', updateSubmit);

    const onEvent = (e) => {
        const ev = JSON.parse(e.data);
        if (ev.type === 'output_audio_buffer.stopped' || ev.type === 'output_audio_buffer.cleared') spoke();
        else if (ev.type === 'conversation.item.input_audio_transcription.completed' && !speaking && !busy && !finished) {
            // Keep each speech segment in an editable draft. The candidate decides when to submit.
            const segment = (ev.transcript || '').trim();
            if (segment) draft.value = [draft.value.trim(), segment].filter(Boolean).join(' ').slice(0, draft.maxLength);
            updateSubmit();
        } else if (ev.type === 'error') console.warn('realtime', ev.error);
    };

    const end = (text) => {
        finished = true; draft.disabled = true; updateSubmit(); status(text);
        setTimeout(() => { if (pc) pc.close(); if (micStream) micStream.getTracks().forEach(track => track.stop()); }, 1500);
    };

    $('agree').addEventListener('change', (e) => { $('start').disabled = !e.target.checked; });
    $('start').addEventListener('click', async () => {
        $('start').disabled = true; $('blocker').textContent = '';
        try { micStream = await navigator.mediaDevices.getUserMedia({audio: true}); } catch {
            $('blocker').textContent = 'Cần cho phép micro để phỏng vấn.'; $('start').disabled = false; return;
        }
        const voice = await rpc('voice');
        if (voice.error) {
            $('blocker').textContent = voice.error === 'closed' ? 'Buổi phỏng vấn đã kết thúc.' : `Không kết nối được dịch vụ giọng nói: ${voice.detail || 'vui lòng thử lại.'}`;
            micStream.getTracks().forEach(track => track.stop()); micStream = null;
            $('start').disabled = false; return;
        }
        pc = new RTCPeerConnection();
        const audio = new Audio(); audio.autoplay = true;
        pc.ontrack = (e) => { audio.srcObject = e.streams[0]; };
        pc.addTrack(micStream.getTracks()[0]);
        dc = pc.createDataChannel('oai-events');
        dc.onmessage = onEvent;
        await pc.setLocalDescription(await pc.createOffer());
        const sdp = await fetch(`https://api.openai.com/v1/realtime/calls?model=${encodeURIComponent(voice.model)}`, {
            method: 'POST', body: pc.localDescription.sdp,
            headers: {Authorization: `Bearer ${voice.secret}`, 'Content-Type': 'application/sdp'},
        });
        if (!sdp.ok) { $('blocker').textContent = 'Không kết nối được dịch vụ giọng nói.';
            micStream.getTracks().forEach(track => track.stop()); micStream = null; pc.close(); $('start').disabled = false; return; }
        await pc.setRemoteDescription({type: 'answer', sdp: await sdp.text()});
        await new Promise((r) => (dc.readyState === 'open' ? r() : dc.addEventListener('open', r, {once: true})));
        $('consent').hidden = true; $('stage').hidden = false;
        status('Đang chuẩn bị câu hỏi...');
        busy = true;
        try { await handle(await rpc('start')); } finally { busy = false; }
    });
})();
