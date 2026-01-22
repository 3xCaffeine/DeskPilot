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
    firefox \
    gedit \
    # --- Python environment ---
    python3 \
    python3-pip \
    # --- PyAutoGUI dependencies ---
    python3-tk \
    python3-dev \
    scrot \
    gnome-screenshot \
    # --- Clean up ---
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────────────────────
# STEP 2: Install Python packages
# ─────────────────────────────────────────────────────────────
# PyAutoGUI:    Mouse/keyboard control
# Pillow:       Screenshot handling
# python-xlib:  X11 bindings (PyAutoGUI needs this on Linux)
RUN pip3 install --no-cache-dir \
    pyautogui \
    pillow \
    python-xlib \
    pyscreeze \
    pydantic

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
