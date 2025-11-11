(function() {
    'use strict';

    console.log('[EXTRA] Script');

    document.addEventListener('DOMContentLoaded', function() {

        if (typeof window.imageData === 'undefined' || !window.imageData || Object.keys(window.imageData).length === 0) {
            return;
        }

        const imageData = window.imageData;
        const originalImg = document.getElementById('originalImage');
        const maskImg = document.getElementById('maskImage');
        const blendedImg = document.getElementById('blendedImage');
        const spinner = document.getElementById('imageSpinner');
        const downloadBtn = document.getElementById('downloadCurrentBtn');

        if (!originalImg || !maskImg || !blendedImg) {
            return;
        }

        // Zoom controls
        const zoomInBtn = document.getElementById('zoomInBtn');
        const zoomOutBtn = document.getElementById('zoomOutBtn');
        const zoomResetBtn = document.getElementById('zoomResetBtn');
        const zoomLevelSpan = document.getElementById('zoomLevel');
        const imageContainer = document.getElementById('imageContainer');

        if (!zoomInBtn || !zoomOutBtn || !zoomResetBtn || !imageContainer) {
            return;
        }

        // +-state control
        let currentZoom = 1.0;
        let currentView = 'original';
        const zoomStep = 0.25;
        const minZoom = 0.5;
        const maxZoom = 4.0;

        const loadedImages = {
            original: false,
            mask: false,
            blended: false
        };

        // etap thumbnails
        // load insta
        function initializeThumbnails() {
            if (imageData.original_thumb) {
                originalImg.src = imageData.original_thumb;
                originalImg.dataset.fullUrl = imageData.original_url;
                originalImg.dataset.downloadUrl = imageData.original_download || imageData.original_url;
                originalImg.onload = () => console.log('[EXTRA] loaded');
                originalImg.onerror = (e) => console.error('[EXTRA] failed', e);
            }

            if (imageData.mask_thumb) {
                maskImg.src = imageData.mask_thumb;
                maskImg.dataset.fullUrl = imageData.mask_url;
                maskImg.dataset.downloadUrl = imageData.mask_download || imageData.mask_url;
                maskImg.onload = () => console.log('[EXTRA] mask loaded');
                maskImg.onerror = (e) => console.error('[EXTRA] mask failed', e);
            }

            if (imageData.blended_thumb) {
                blendedImg.src = imageData.blended_thumb;
                blendedImg.dataset.fullUrl = imageData.blended_url;
                blendedImg.dataset.downloadUrl = imageData.blended_download || imageData.blended_url;
                blendedImg.onload = () => console.log('[EXTRA] blended loaded');
                blendedImg.onerror = (e) => console.error('[EXTRA] blended failed', e);
            }
        }
        // FULL STAGE
        function loadFullImage(img, type) {
            if (loadedImages[type] || !img.dataset.fullUrl) {
                return;
            }

            console.log(`[EXTRA] full ${type} image...`);

            if (spinner) spinner.style.display = 'block';
            img.classList.add('loading');

            const fullImg = new Image();
            fullImg.onload = function() {
                img.src = img.dataset.fullUrl;
                loadedImages[type] = true;
                img.classList.remove('loading');
                if (spinner) spinner.style.display = 'none';
                console.log(`[EXTRA] loaded full ${type} image`);
            };
            fullImg.onerror = function(e) {
                console.error(`[EXTRA] failed full image ${type}`, e);
                img.classList.remove('loading');
                if (spinner) spinner.style.display = 'none';
            };
            fullImg.src = img.dataset.fullUrl;
        }
        function setupViewControls() {
            document.querySelectorAll('.image-control-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const view = this.dataset.view;
                    currentView = view;
                    document.querySelectorAll('.image-control-btn').forEach(b => {
                        b.classList.remove('active');
                    });
                    this.classList.add('active');

                    document.querySelectorAll('.image-layer').forEach(layer => {
                        layer.style.opacity = '0';
                    });
                    const targetLayer = document.querySelector(`[data-layer="${view}"]`);
                    if (targetLayer) {
                        targetLayer.style.opacity = '1';
                    }
                    const img = targetLayer ? targetLayer.querySelector('img') : null;
                    if (img && !loadedImages[view]) {
                        loadFullImage(img, view);
                    }
                });
            });
        }

        function downloadCurrentView() {
            let img, filename;
            if (currentView === 'original') {
                img = originalImg;
                filename = 'wojewodztwo_original.jpg';
            } else if (currentView === 'mask') {
                img = maskImg;
                filename = 'wojewodztwo_mask.png';
            } else if (currentView === 'blended') {
                img = blendedImg;
                filename = 'wojewodztwo_overlay.png';
            }

            if (!img || !img.dataset.downloadUrl) {
                console.error('[EXTRA] No download URL for current view');
                return;
            }

            const link = document.createElement('a');
            link.href = img.dataset.downloadUrl;
            link.download = filename;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            console.log('[EXTRA] Download:', filename);
        }
        if (downloadBtn) {
            downloadBtn.addEventListener('click', downloadCurrentView);
        }

        function updateZoom(newZoom) {
            currentZoom = Math.max(minZoom, Math.min(maxZoom, newZoom));

            document.querySelectorAll('.zoomable-image').forEach(img => {
                img.style.transform = `scale(${currentZoom})`;
                img.style.transformOrigin = 'center center';
            });

            if (zoomLevelSpan) {
                zoomLevelSpan.textContent = `${Math.round(currentZoom * 100)}%`;
            }

            if (currentZoom > 1.0) {
                imageContainer.classList.add('zoom-out');
                imageContainer.classList.remove('zoom-in');
            } else {
                imageContainer.classList.add('zoom-in');
                imageContainer.classList.remove('zoom-out');
            }

            if (zoomInBtn) zoomInBtn.disabled = currentZoom >= maxZoom;
            if (zoomOutBtn) zoomOutBtn.disabled = currentZoom <= minZoom;
        }

        function setupZoomControls() {
            if (zoomInBtn) {
                zoomInBtn.addEventListener('click', () => {
                    updateZoom(currentZoom + zoomStep);
                });
            }

            if (zoomOutBtn) {
                zoomOutBtn.addEventListener('click', () => {
                    updateZoom(currentZoom - zoomStep);
                });
            }

            if (zoomResetBtn) {
                zoomResetBtn.addEventListener('click', () => {
                    updateZoom(1.0);
                    imageContainer.scrollTop = 0;
                    imageContainer.scrollLeft = 0;
                });
            }
        }

        function setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                    return;
                }

                if (e.key === '+' || e.key === '=') {
                    e.preventDefault();
                    updateZoom(currentZoom + zoomStep);
                } else if (e.key === '-' || e.key === '_') {
                    e.preventDefault();
                    updateZoom(currentZoom - zoomStep);
                } else if (e.key === '0') {
                    e.preventDefault();
                    updateZoom(1.0);
                }
            });
        }

        function setupMouseWheelZoom() {
            imageContainer.addEventListener('wheel', (e) => {
                if (e.ctrlKey) {
                    e.preventDefault();
                    const delta = e.deltaY > 0 ? -zoomStep : zoomStep;
                    updateZoom(currentZoom + delta);
                }
            }, { passive: false });
        }

        function setupDragToPan() {
            let isDragging = false;
            let startX, startY, scrollLeft, scrollTop;

            imageContainer.addEventListener('mousedown', (e) => {
                if (currentZoom <= 1.0) return;
                isDragging = true;
                imageContainer.classList.add('grabbing');
                startX = e.pageX - imageContainer.offsetLeft;
                startY = e.pageY - imageContainer.offsetTop;
                scrollLeft = imageContainer.scrollLeft;
                scrollTop = imageContainer.scrollTop;
            });

            imageContainer.addEventListener('mouseleave', () => {
                isDragging = false;
                imageContainer.classList.remove('grabbing');
            });

            imageContainer.addEventListener('mouseup', () => {
                isDragging = false;
                imageContainer.classList.remove('grabbing');
            });

            imageContainer.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                e.preventDefault();
                const x = e.pageX - imageContainer.offsetLeft;
                const y = e.pageY - imageContainer.offsetTop;
                const walkX = (x - startX) * 2;
                const walkY = (y - startY) * 2;
                imageContainer.scrollLeft = scrollLeft - walkX;
                imageContainer.scrollTop = scrollTop - walkY;
            });
        }

        initializeThumbnails();
        setupViewControls();
        setupZoomControls();
        setupKeyboardShortcuts();
        setupMouseWheelZoom();
        setupDragToPan();

        setTimeout(() => {
            loadFullImage(originalImg, 'original');
        }, 1000);
    });
})();