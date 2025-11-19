// Async Image Generation with Progress Loading

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function generateImageAsync(projectId, sceneId) {
    const generateBtn = document.getElementById('generateBtn');
    const imageContainer = document.getElementById('imageContainer');
    const progressLoader = document.getElementById('progressLoader');
    const progressMessage = document.getElementById('progressMessage');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    const initialContainer = document.getElementById('initialContainer');

    // Hide error alert if visible
    errorAlert.style.display = 'none';

    // Hide initial container if it exists
    if (initialContainer) {
        initialContainer.style.display = 'none';
    }

    // Disable button and show loader
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating...';
    progressLoader.style.display = 'block';
    imageContainer.style.display = 'none';

    // Progress messages to cycle through
    const progressMessages = [
        'Initializing image generation...',
        'Processing scene prompt...',
        'Preparing character descriptions...',
        'Connecting to Nano Banana...',
        'Generating image with AI...',
        'Applying artistic style...',
        'Finalizing image...'
    ];

    let messageIndex = 0;
    const messageInterval = setInterval(() => {
        if (messageIndex < progressMessages.length) {
            progressMessage.textContent = progressMessages[messageIndex];
            messageIndex++;
        } else {
            progressMessage.textContent = 'This may take 20-30 seconds...';
        }
    }, 3000);

    // Make AJAX request
    fetch(`/project/${projectId}/scene/${sceneId}/generate-ajax/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        clearInterval(messageInterval);

        if (data.status === 'success') {
            // Success - show the generated image
            progressMessage.textContent = 'Image generated successfully!';

            // Update image container with new image
            setTimeout(() => {
                progressLoader.style.display = 'none';
                imageContainer.style.display = 'block';

                // Update or create image element
                let imgElement = imageContainer.querySelector('img');
                if (!imgElement) {
                    imgElement = document.createElement('img');
                    imgElement.className = 'img-fluid rounded';
                    imageContainer.innerHTML = '';
                    imageContainer.appendChild(imgElement);
                }

                // Add fade-in effect
                imgElement.style.opacity = '0';
                imgElement.src = data.image_url;
                imgElement.onload = () => {
                    imgElement.style.transition = 'opacity 0.5s ease-in';
                    imgElement.style.opacity = '1';
                };

                // Update button
                generateBtn.disabled = false;
                generateBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Regenerate Image';
                generateBtn.className = 'btn btn-warning';

                // Show success notification
                showNotification('Image generated successfully!', 'success');
            }, 1000);

        } else {
            // Error occurred
            progressLoader.style.display = 'none';
            errorAlert.style.display = 'block';
            errorMessage.textContent = data.message || 'An error occurred during generation.';

            // Show initial container again if no image exists
            if (initialContainer && !imageContainer.querySelector('img')) {
                initialContainer.style.display = 'block';
            }

            // Re-enable button
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="bi bi-magic"></i> Generate Image with Nano Banana';
        }
    })
    .catch(error => {
        clearInterval(messageInterval);
        console.error('Error:', error);

        progressLoader.style.display = 'none';
        errorAlert.style.display = 'block';
        errorMessage.textContent = 'Network error. Please check your connection and try again.';

        // Show initial container again if no image exists
        if (initialContainer && !imageContainer.querySelector('img')) {
            initialContainer.style.display = 'block';
        }

        // Re-enable button
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="bi bi-magic"></i> Generate Image with Nano Banana';
    });
}

function showNotification(message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    notification.style.zIndex = '9999';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Separate function for editing images
function editImageAsync(projectId, sceneId) {
    const editBtn = document.getElementById('editBtn');
    const editPromptField = document.getElementById('edit_prompt_field');
    const imageContainer = document.getElementById('imageContainer');
    const progressLoader = document.getElementById('progressLoader');
    const progressMessage = document.getElementById('progressMessage');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');

    // Get the edit prompt
    const editPrompt = editPromptField.value.trim();
    if (!editPrompt) {
        showNotification('Please enter edit instructions', 'warning');
        editPromptField.focus();
        return;
    }

    // Hide error alert if visible
    errorAlert.style.display = 'none';

    // Disable button and show loader
    editBtn.disabled = true;
    editBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Editing...';
    progressLoader.style.display = 'block';
    imageContainer.style.display = 'none';

    // Set progress message for editing
    progressMessage.textContent = 'Applying edits to your image...';

    // Make AJAX request to the edit endpoint
    fetch(`/project/${projectId}/scene/${sceneId}/edit-ajax/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ edit_prompt: editPrompt })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Success - show the edited image
            progressMessage.textContent = 'Image edited successfully!';

            // Update image container with new image
            setTimeout(() => {
                progressLoader.style.display = 'none';
                imageContainer.style.display = 'block';

                // Update or create image element
                let imgElement = imageContainer.querySelector('img');
                if (!imgElement) {
                    imgElement = document.createElement('img');
                    imgElement.className = 'img-fluid rounded';
                    imageContainer.innerHTML = '';
                    imageContainer.appendChild(imgElement);
                }

                // Add fade-in effect
                imgElement.style.opacity = '0';
                imgElement.src = data.image_url;
                imgElement.onload = () => {
                    imgElement.style.transition = 'opacity 0.5s ease-in';
                    imgElement.style.opacity = '1';
                };

                // Re-enable button
                editBtn.disabled = false;
                editBtn.innerHTML = '<i class="bi bi-magic"></i> Apply Edit';

                // Show success notification
                showNotification('Image edited successfully!', 'success');
            }, 1000);

        } else {
            // Error occurred
            progressLoader.style.display = 'none';
            errorAlert.style.display = 'block';
            errorMessage.textContent = data.message || 'An error occurred during editing.';
            imageContainer.style.display = 'block';

            // Re-enable button
            editBtn.disabled = false;
            editBtn.innerHTML = '<i class="bi bi-magic"></i> Apply Edit';
        }
    })
    .catch(error => {
        console.error('Error:', error);

        progressLoader.style.display = 'none';
        errorAlert.style.display = 'block';
        errorMessage.textContent = 'Network error. Please check your connection and try again.';
        imageContainer.style.display = 'block';

        // Re-enable button
        editBtn.disabled = false;
        editBtn.innerHTML = '<i class="bi bi-magic"></i> Apply Edit';
    });
}