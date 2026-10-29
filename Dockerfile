FROM odoo:latest
USER root
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed typing_extensions anthropic edge-tts
USER odoo
