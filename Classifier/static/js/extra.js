document.addEventListener("DOMContentLoaded", function() {
    const imageData = window.imageData || {};
    const config = window.AppConfig || {};

    if (!config.hasAnalysis) {
        return;
    }

    const imageContainer = document.getElementById('imageContainer');
    const originalImg = document.getElementById('originalImage');
    const maskImg = document.getElementById('maskImage');
    const blendedImg = document.getElementById('blendedImage');
    const imageSpinner = document.getElementById('imageSpinner');

    let currentScale = 1;
    let isDragging = false;
    let startX, startY, scrollLeft, scrollTop;

    const images = {
        'original': originalImg,
        'mask': maskImg,
        'blended': blendedImg
    };

    function loadImage(imgElement, thumbKey, fullKey) {
        if (!imageData[thumbKey]) {
            console.log(`No thumbnail for ${thumbKey}`);
            return;
        }

        imgElement.src = imageData[thumbKey];

        imgElement.style.cursor = 'pointer';

        // etap thumbnails
        // load insta
        imgElement.addEventListener('click', function loadFullRes() {
            if (imageData[fullKey]) {
                imageSpinner.style.display = 'block';

                const fullImg = new Image();
                fullImg.onload = () => {
                    imgElement.src = imageData[fullKey];
                    imageSpinner.style.display = 'none';
                    imgElement.style.cursor = 'grab';
                };
                fullImg.onerror = () => {
                    imageSpinner.style.display = 'none';
                    console.error('Failed to load full resolution image');
                };
                fullImg.src = imageData[fullKey];

                imgElement.removeEventListener('click', loadFullRes);
            }
        });
    }

    if (imageData.has_original && imageData.original_thumb) {
        loadImage(originalImg, 'original_thumb', 'original_url');
    }

    if (imageData.has_mask && imageData.mask_thumb) {
        loadImage(maskImg, 'mask_thumb', 'mask_url');
    }

    if (imageData.has_blended && imageData.blended_thumb) {
        loadImage(blendedImg, 'blended_thumb', 'blended_url');
    }

    function updateZoom(newScale) {
        currentScale = Math.max(1, Math.min(5, newScale));

        Object.values(images).forEach(img => {
            img.style.transform = `scale(${currentScale})`;
        });

        document.getElementById('zoomLevel').textContent = `${Math.round(currentScale * 100)}%`;

        if (currentScale > 1) {
            imageContainer.style.cursor = 'grab';
            imageContainer.style.overflow = 'auto';
        } else {
            imageContainer.style.cursor = 'default';
            imageContainer.style.overflow = 'hidden';
        }
    }

    document.getElementById('zoomInBtn').addEventListener('click', () => {
        updateZoom(currentScale + 0.25);
    });

    document.getElementById('zoomOutBtn').addEventListener('click', () => {
        updateZoom(currentScale - 0.25);
    });

    document.getElementById('zoomResetBtn').addEventListener('click', () => {
        updateZoom(1);
        imageContainer.scrollLeft = 0;
        imageContainer.scrollTop = 0;
    });

    imageContainer.addEventListener('mousedown', (e) => {
        if (currentScale <= 1) return;
        isDragging = true;
        imageContainer.style.cursor = 'grabbing';
        startX = e.pageX - imageContainer.offsetLeft;
        startY = e.pageY - imageContainer.offsetTop;
        scrollLeft = imageContainer.scrollLeft;
        scrollTop = imageContainer.scrollTop;
    });

    imageContainer.addEventListener('mouseleave', () => {
        isDragging = false;
        if (currentScale > 1) {
            imageContainer.style.cursor = 'grab';
        }
    });

    imageContainer.addEventListener('mouseup', () => {
        isDragging = false;
        if (currentScale > 1) {
            imageContainer.style.cursor = 'grab';
        }
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

    imageContainer.addEventListener('wheel', (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        updateZoom(currentScale + delta);
    });

    document.getElementById('downloadCurrentBtn').addEventListener('click', () => {
        const activeBtn = document.querySelector('.image-control-btn.active');
        if (!activeBtn) return;

        const view = activeBtn.dataset.view;
        const analysisId = config.analysisId;

        if (!analysisId) {
            console.error('No analysis ID available');
            return;
        }

        window.location.href = `/wojewodztwo/${analysisId}/download/${view}/`;
    });
});