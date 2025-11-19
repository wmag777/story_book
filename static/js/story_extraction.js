// Story Extraction Form Handler with Loading Indicators

function initializeStoryExtraction() {
    const form = document.getElementById('storyExtractionForm');
    const submitBtn = document.getElementById('extractBtn');
    const storyTextarea = document.getElementById('story_text');
    const progressLoader = document.getElementById('progressLoader');
    const progressMessage = document.getElementById('progressMessage');
    const formCard = document.getElementById('formCard');

    if (!form || !submitBtn) return;

    // Handle form submission
    form.addEventListener('submit', function(e) {
        // Validate story text
        const storyText = storyTextarea.value.trim();
        if (!storyText) {
            e.preventDefault();
            showNotification('Please enter your story text', 'warning');
            storyTextarea.focus();
            return;
        }

        // Check if story is reasonably long
        if (storyText.length < 100) {
            e.preventDefault();
            if (!confirm('Your story seems very short. Are you sure you want to continue?')) {
                return;
            }
        }

        // Disable submit button and show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        // Disable textarea to prevent editing during submission
        storyTextarea.readOnly = true;

        // Show progress loader
        if (progressLoader) {
            progressLoader.style.display = 'block';

            // Progress messages to cycle through
            const progressMessages = [
                'Analyzing your story...',
                'Identifying main characters...',
                'Extracting character descriptions...',
                'Detecting scene boundaries...',
                'Processing with AI...',
                'Organizing scenes for illustration...',
                'Creating character placeholders...',
                'Finalizing extraction...'
            ];

            let messageIndex = 0;

            // Initial message
            if (progressMessage) {
                progressMessage.textContent = progressMessages[0];
            }

            // Cycle through messages
            const messageInterval = setInterval(() => {
                messageIndex++;
                if (messageIndex < progressMessages.length) {
                    if (progressMessage) {
                        progressMessage.textContent = progressMessages[messageIndex];
                    }
                } else {
                    if (progressMessage) {
                        progressMessage.textContent = 'This may take 20-30 seconds for longer stories...';
                    }
                }
            }, 3000);

            // Store interval ID to clear it if needed (though page will reload)
            form.dataset.messageInterval = messageInterval;
        }

        // Add visual feedback to the form card
        if (formCard) {
            formCard.style.opacity = '0.7';
        }

        // Show a notification
        showNotification('Processing your story with AI. Please wait...', 'info');
    });
}

function showNotification(message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            ${getNotificationIcon(type)}
            <div class="ms-2">${message}</div>
            <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert"></button>
        </div>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds for non-info messages
    if (type !== 'info') {
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

function getNotificationIcon(type) {
    switch(type) {
        case 'success':
            return '<i class="bi bi-check-circle-fill text-success"></i>';
        case 'warning':
            return '<i class="bi bi-exclamation-triangle-fill text-warning"></i>';
        case 'danger':
            return '<i class="bi bi-x-circle-fill text-danger"></i>';
        case 'info':
        default:
            return '<i class="bi bi-info-circle-fill text-info"></i>';
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initializeStoryExtraction);