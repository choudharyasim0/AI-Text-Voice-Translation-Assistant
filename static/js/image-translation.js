(() => {
    const tab = document.getElementById('imageTranslationTab');
    const pane = document.getElementById('image-translation-section');
    const fileInput = document.getElementById('imageTranslationFile');
    const sourceSelect = document.getElementById('imageTranslationSource');
    const targetSelect = document.getElementById('imageTranslationTarget');
    const submitButton = document.getElementById('translateImageBtn');
    const extractedOutput = document.getElementById('imageExtractedText');
    const translatedOutput = document.getElementById('imageTranslatedText');

    if (!tab || !pane || !submitButton) return;

    const showImageTab = () => {
        document.querySelectorAll('.section-pane').forEach((section) => section.classList.remove('active'));
        document.querySelectorAll('.menu-item').forEach((item) => item.classList.remove('active'));
        pane.classList.add('active');
        tab.classList.add('active');
    };

    tab.addEventListener('click', showImageTab);
    tab.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            showImageTab();
        }
    });

    submitButton.addEventListener('click', async () => {
        const imageFile = fileInput?.files?.[0];
        if (!imageFile) {
            showToast('Please choose an image first.', 'error');
            return;
        }
        if (!imageFile.type.startsWith('image/')) {
            showToast('Please choose a valid image file.', 'error');
            return;
        }
        if (imageFile.size > 8 * 1024 * 1024) {
            showToast('Image must be 8 MB or smaller.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('source', sourceSelect?.value || 'auto');
        formData.append('target', targetSelect?.value || 'en');

        submitButton.disabled = true;
        const originalLabel = submitButton.textContent;
        submitButton.textContent = 'Processing image...';
        if (extractedOutput) extractedOutput.value = '';
        if (translatedOutput) translatedOutput.value = '';

        try {
            const response = await fetch('/translate-image', {
                method: 'POST',
                body: formData,
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Image translation failed.');
            }

            if (extractedOutput) extractedOutput.value = result.extracted_text || '';
            if (translatedOutput) translatedOutput.value = result.translation || '';
            showToast('Image translation complete.', 'success');
        } catch (error) {
            showToast(error.message || 'Image translation failed.', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = originalLabel;
        }
    });
})();
