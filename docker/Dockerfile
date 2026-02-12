# Dockerfile - Ubuntu Desktop in a Container
# ============================================
# This creates a Linux desktop you can control programmatically.
# 
# WHAT'S INSIDE:
# - Ubuntu 22.04 as the base
# - XFCE (lightweight desktop)
# - Xvfb (virtual display)
# - x11vnc (VNC server to view the desktop)
# - Python + PyAutoGUI (to control mouse/keyboard)

FROM ubuntu:22.04

# Prevent interactive prompts during apt-get
ENV DEBIAN_FRONTEND=noninteractive

# ─────────────────────────────────────────────────────────────
# STEP 0: Use working mirror (archive.ubuntu.com has issues)
# ─────────────────────────────────────────────────────────────
RUN sed -i 's|http://archive.ubuntu.com|http://mirrors.edge.kernel.org|g' /etc/apt/sources.list

# ─────────────────────────────────────────────────────────────
# STEP 1: Install system packages
# ─────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    # --- Desktop environment ---
    xfce4 \
    xfce4-terminal \
    # --- Virtual display + VNC ---
    xvfb \
    x11vnc \
    # --- noVNC (browser-based VNC) ---
    novnc \
    websockify \
    # --- Process supervisor ---
    supervisor \
    # --- Useful apps for testing ---
    gedit \
    mousepad \ 
    # --- Python environment ---
    python3 \
    python3-pip \
    # --- PyAutoGUI dependencies ---
    python3-tk \
    python3-dev \
    scrot \
    gnome-screenshot \
    # --- Accessibility + OCR tools ---
    xdotool \
    wmctrl \
    tesseract-ocr \
    # --- Chrome dependencies ---
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    xdg-utils \
    dbus-x11 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────────────────────
# STEP 1b: Install Google Chrome
# ─────────────────────────────────────────────────────────────
RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────────────────────
# STEP 1c: Create Chrome wrapper script and modify .desktop file
# ─────────────────────────────────────────────────────────────
# This ensures Chrome ALWAYS launches with CDP enabled,
# and suppresses first-run / sign-in UI so the agent isn't confused.
RUN mkdir -p /etc/opt/chrome/policies/managed && \
    echo '{\n  "BrowserAddPersonEnabled": false,\n  "DefaultBrowserSettingEnabled": false,\n  "ShowFirstRunBubble": false,\n  "RestoreOnStartup": 0,\n  "SigninAllowed": false\n}' > /etc/opt/chrome/policies/managed/managed_policies.json && \
    echo '#!/bin/bash\n\
exec /usr/bin/google-chrome-stable \\\n\
  --no-sandbox \\\n\
  --disable-gpu \\\n\
  --disable-dev-shm-usage \\\n\
  --remote-debugging-port=9222 \\\n\
  --user-data-dir=/tmp/chrome-profile \\\n\
  --disable-infobars \\\n\
  --no-first-run \\\n\
  --no-default-browser-check \\\n\
  --disable-sync \\\n\
  --disable-default-apps \\\n\
  --disable-background-networking \\\n\
  --disable-component-update \\\n\
  --safebrowsing-disable-auto-update \\\n\
  --disable-translate \\\n\
  --disable-features=TranslateUI,PasswordManagerOnboarding \\\n\
  --start-maximized \\\n\
  --test-type \\\n\
  "$@"' > /usr/local/bin/chrome-with-cdp && \
    chmod +x /usr/local/bin/chrome-with-cdp && \
    sed -i 's|Exec=/usr/bin/google-chrome-stable|Exec=/usr/local/bin/chrome-with-cdp|g' /usr/share/applications/google-chrome.desktop && \
    update-desktop-database /usr/share/applications/ && \
    ln -sf /usr/local/bin/chrome-with-cdp /usr/bin/google-chrome && \
    ln -sf /usr/local/bin/chrome-with-cdp /usr/local/bin/google-chrome

# ─────────────────────────────────────────────────────────────
# STEP 2: Install Python packages
# ─────────────────────────────────────────────────────────────
RUN pip3 install --no-cache-dir \
    pyautogui \
    pillow \
    python-xlib \
    pyscreeze \
    pydantic \
    dspy \
    google-genai \
    litellm \
    pytesseract \
    playwright \
    nest-asyncio

# Install Playwright browsers (Chromium only - we use system Chrome for CDP)
RUN playwright install-deps chromium

# ─────────────────────────────────────────────────────────────
# STEP 3: Configure the environment
# ─────────────────────────────────────────────────────────────
# Tell ALL processes to use display :99
ENV DISPLAY=:99

# PyAutoGUI safety feature - disable the "move to corner to abort" behavior
# (We're in a container, no need for this safety)
ENV PYAUTOGUI_FAILSAFE=False

# Copy our supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directory
RUN mkdir -p /var/log

# ─────────────────────────────────────────────────────────────
# STEP 4: Set up working directory
# ─────────────────────────────────────────────────────────────
WORKDIR /app

# Expose VNC port (connect with VNC viewer to see desktop)
EXPOSE 5900

# Start supervisor (which starts Xvfb, XFCE, and VNC)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
