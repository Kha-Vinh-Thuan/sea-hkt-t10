import asyncio
import base64
import logging

_logger = logging.getLogger(__name__)

VOICE = 'vi-VN-HoaiMyNeural'  # natural Vietnamese neural voice; alt: vi-VN-NamMinhNeural (male)
TIMEOUT = 12  # seconds; first call after a restart is slow (~8s), later ones ~1s


def tts(text):
    """Vietnamese neural speech as base64 MP3, or None so the browser falls back to its own voice.

    ponytail: edge-tts uses Microsoft Edge's public read-aloud endpoint (no key, no SLA);
    swap for Azure Speech / Google TTS with a key when this goes to production.
    """
    try:
        import edge_tts
    except ImportError:
        return None

    async def run():
        audio = bytearray()
        async for chunk in edge_tts.Communicate(text, VOICE, rate='+5%').stream():
            if chunk['type'] == 'audio':
                audio += chunk['data']
        return bytes(audio)

    try:
        audio = asyncio.run(asyncio.wait_for(run(), TIMEOUT))
    except Exception as e:  # noqa: BLE001 - voice is best effort, the interview must go on
        _logger.warning("TTS failed, browser voice fallback: %s", e)
        return None
    return base64.b64encode(audio).decode() if audio else None
