/**
 * SI BMC — Mouse Event Handler
 * Utility module for mouse coordinate processing.
 * Main mouse logic is in kvm.js; this provides helpers.
 */

const MouseHandler = {
    /**
     * Calculate the actual rendered area of a video element
     * with object-fit: contain, accounting for letterboxing.
     */
    getVideoRenderRect(videoEl) {
        const rect = videoEl.getBoundingClientRect();
        const naturalW = videoEl.naturalWidth || 1920;
        const naturalH = videoEl.naturalHeight || 1080;
        const videoAspect = naturalW / naturalH;
        const containerAspect = rect.width / rect.height;

        let renderW, renderH, offsetX, offsetY;

        if (containerAspect > videoAspect) {
            renderH = rect.height;
            renderW = renderH * videoAspect;
            offsetX = (rect.width - renderW) / 2;
            offsetY = 0;
        } else {
            renderW = rect.width;
            renderH = renderW / videoAspect;
            offsetX = 0;
            offsetY = (rect.height - renderH) / 2;
        }

        return {
            x: rect.left + offsetX,
            y: rect.top + offsetY,
            width: renderW,
            height: renderH,
            containerRect: rect,
        };
    },

    /**
     * Convert client coordinates to normalized video coordinates (0-1).
     */
    clientToVideo(clientX, clientY, videoEl) {
        const render = this.getVideoRenderRect(videoEl);
        let x = (clientX - render.x) / render.width;
        let y = (clientY - render.y) / render.height;
        x = Math.max(0, Math.min(1, x));
        y = Math.max(0, Math.min(1, y));
        return { x, y };
    },

    /**
     * Convert touch event to normalized video coordinates.
     */
    touchToVideo(touch, videoEl) {
        return this.clientToVideo(touch.clientX, touch.clientY, videoEl);
    },

    /**
     * Map mouse button number to HID button index.
     * Browser: 0=left, 1=middle, 2=right
     * HID: 0=left, 1=right, 2=middle
     */
    mapButton(browserButton) {
        const map = { 0: 0, 1: 2, 2: 1 };
        return map[browserButton] ?? browserButton;
    },
};
