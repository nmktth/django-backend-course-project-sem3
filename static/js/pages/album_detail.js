document.addEventListener('DOMContentLoaded', function() {
    // Shared functionality
    const copyBtn = document.querySelector('.btn-copy');
    if (copyBtn) {
        copyBtn.addEventListener('click', copyLink);
    }
    
    const fileInput = document.getElementById('file-upload');
    const uploadLabel = document.getElementById('upload-label');
    const fullScreenLoader = document.getElementById('full-screen-loader');

    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                 // Size validation
                 const MAX_SIZE = 10 * 1024 * 1024; // 10MB
                 let hasOversizedFile = false;
                 
                 Array.from(this.files).forEach(file => {
                     if (file.size > MAX_SIZE) {
                         hasOversizedFile = true;
                     }
                 });
 
                 if (hasOversizedFile) {
                     alert('Ошибка: Один или несколько файлов превышают лимит в 10 МБ. Пожалуйста, выберите файлы меньшего размера.');
                     this.value = ''; // Reset input
                     return;
                 }

                // UI Feedback: Full Screen Loader
                if (fullScreenLoader) {
                    fullScreenLoader.style.display = 'flex';
                }
                
                // Hide button just in case, though overlay covers it
                if (uploadLabel) uploadLabel.style.display = 'none';

                // UI Feedback: Grid Previews (still keep this as background context)
                const photosGrid = document.querySelector('.photos-grid');
                if (photosGrid) {
                    const emptyMsg = document.querySelector('.empty-album');
                    if (emptyMsg) emptyMsg.style.display = 'none';

                    Array.from(this.files).forEach(file => {
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            const card = document.createElement('div');
                            card.className = 'photo-card uploading';
                            card.innerHTML = `
                                <img src="${e.target.result}" class="photo-img" style="object-fit: cover;">
                                <div class="upload-overlay">
                                    <i class="fas fa-spinner fa-spin fa-2x"></i>
                                </div>
                            `;
                            // Insert at the beginning of the grid
                           photosGrid.insertBefore(card, photosGrid.firstChild);
                        };
                        reader.readAsDataURL(file);
                    });
                }

                // Delay submit slightly to allow UI updates to render
                setTimeout(() => {
                    this.form.submit();
                }, 500); // Increased delay a bit to let the loader animation start smoothly
            }
        });
    }

    const deleteBtn = document.getElementById('btn-delete-album');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Вы уверены, что хотите удалить этот альбом? Это действие нельзя отменить.')) {
                document.getElementById('delete-album-form').submit();
            }
        });
    }

    // Lightbox functionality
    let currentPhotoIndex = 0;
    let photoImages = [];
    const photoImgs = document.querySelectorAll('.photo-img');
    photoImages = Array.from(photoImgs).map(img => img.src);
    
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightbox-img');
    const counter = document.getElementById('lightbox-counter');
    const closeBtn = document.querySelector('.lightbox-close');
    const prevBtn = document.querySelector('.lightbox-prev');
    const nextBtn = document.querySelector('.lightbox-next');

    if (lightbox) {
        photoImgs.forEach((img, index) => {
            img.style.cursor = 'pointer'; // Ensure pointer cursor
            img.addEventListener('click', () => openLightbox(index));
        });

        if (closeBtn) closeBtn.addEventListener('click', closeLightbox);
        
        if (prevBtn) prevBtn.addEventListener('click', () => changePhoto(-1));
        
        if (nextBtn) nextBtn.addEventListener('click', () => changePhoto(1));

        // Close on background click
        lightbox.addEventListener('click', function(e) {
            if (e.target === lightbox) {
                closeLightbox();
            }
        });

        // Keyboard navigation
        document.addEventListener('keydown', function(e) {
            if (lightbox.style.display === 'flex') {
                if (e.key === 'Escape') closeLightbox();
                if (e.key === 'ArrowLeft') changePhoto(-1);
                if (e.key === 'ArrowRight') changePhoto(1);
            }
        });
    }

    function openLightbox(index) {
        currentPhotoIndex = index;
        updateLightbox();
        lightbox.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function closeLightbox() {
        lightbox.style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    function changePhoto(direction) {
        currentPhotoIndex += direction;
        
        if (currentPhotoIndex < 0) {
            currentPhotoIndex = photoImages.length - 1;
        } else if (currentPhotoIndex >= photoImages.length) {
            currentPhotoIndex = 0;
        }
        
        updateLightbox();
    }

    function updateLightbox() {
        lightboxImg.src = photoImages[currentPhotoIndex];
        counter.textContent = `${currentPhotoIndex + 1} / ${photoImages.length}`;
    }

    function copyLink() {
        var copyText = document.getElementById('shareLink');
        copyText.select();
        copyText.setSelectionRange(0, 99999);
        navigator.clipboard.writeText(copyText.value)
            .then(() => alert('Ссылка скопирована в буфер обмена!'))
            .catch(err => console.error('Ошибка копирования:', err));
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('sharePhotoModal');
    if (!modal) return;

    const input = document.getElementById('photoShareLink');
    const loading = document.getElementById('shareLoading');
    const content = document.getElementById('shareContent');
    const closeBtn = modal.querySelector('.close-modal');
    const copyBtn = modal.querySelector('#copyLinkBtn');
    const disableBtn = modal.querySelector('#disableLinkBtn');
    let currentPhotoId = null;

    // Open Modal Triggers
    document.querySelectorAll('.btn-share-photo').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const photoId = this.dataset.photoId;
            openShareModal(photoId);
        });
    });

    // Close Modal Trigger
    if (closeBtn) {
        closeBtn.addEventListener('click', closeShareModal);
    }
    
    // Close on outside click
    window.addEventListener('click', function(event) {
        if (event.target == modal) {
            closeShareModal();
        }
    });

    // Copy Link Trigger
    if (copyBtn) {
        copyBtn.addEventListener('click', copyPhotoLink);
    }

    // Disable Link Trigger
    if (disableBtn) {
        disableBtn.addEventListener('click', disablePhotoLink);
    }

    function openShareModal(photoId) {
        currentPhotoId = photoId;
        modal.style.display = 'block';
        loading.classList.remove('hidden');
        content.classList.add('hidden');
        loading.style.display = 'block';
        content.style.display = 'none';

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        fetch(`/dashboard/photo/${photoId}/share/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: 'action=generate' // Request to generate/get link
        })
        .then(response => response.json())
        .then(data => {
            loading.style.display = 'none';
            loading.classList.add('hidden');
            
            if(data.status === 'ok') {
                content.classList.remove('hidden');
                content.style.display = 'block';
                input.value = data.link;
            } else {
                alert("Error: " + data.message);
                closeShareModal();
            }
        })
        .catch(err => {
            console.error(err);
            loading.innerText = "Ошибка загрузки";
        });
    }

    function closeShareModal() {
        modal.style.display = 'none';
        currentPhotoId = null;
    }

    function copyPhotoLink() {
        input.select();
        navigator.clipboard.writeText(input.value)
             .then(() => alert("Ссылка скопирована!"))
             .catch(err => console.error(err));
    }

    function disablePhotoLink() {
        if(!currentPhotoId) return;
        
        if(!confirm("Вы уверены? Ссылка перестанет работать.")) return;

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        fetch(`/dashboard/photo/${currentPhotoId}/share/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: 'action=disable'
        })
        .then(response => response.json())
        .then(data => {
            if(data.status === 'ok') {
                alert("Ссылка отключена.");
                closeShareModal();
            } else {
                alert("Error: " + data.message);
            }
        })
        .catch(err => console.error(err));
    }
});
