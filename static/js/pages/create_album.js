document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('id_photos');
  const dropZone = document.getElementById('drop-zone');
  const previewContainer = document.getElementById('preview-container');
  const fileListInfo = document.getElementById('file-list');

  // We use DataTransfer to hold the files because we can't directly manipulate FileList
  const dt = new DataTransfer();

  // Trigger file input click
  dropZone.addEventListener('click', (e) => {
    input.click();
  });

  // Handle file selection
  input.addEventListener('change', (e) => {
    addFiles(input.files);
  });

  // Drag and Drop
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--primary-color)';
    dropZone.style.backgroundColor = 'rgba(74, 144, 226, 0.1)';
  });

  dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#ccc';
    dropZone.style.backgroundColor = 'transparent';
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#ccc';
    dropZone.style.backgroundColor = 'transparent';
    addFiles(e.dataTransfer.files);
  });

  function addFiles(files) {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];

      // Avoid duplicates (optional, based on name and size)
      let isDuplicate = false;
      for (let j = 0; j < dt.items.length; j++) {
        const existingFile = dt.items[j].getAsFile();
        if (existingFile.name === file.name && existingFile.size === file.size) {
          isDuplicate = true;
          break;
        }
      }

      if (!isDuplicate) {
        dt.items.add(file);
        createPreview(file);
      }
    }
    updateInputFiles();
    updateInfo();
  }

  function createPreview(file) {
    const previewCard = document.createElement('div');
    previewCard.className = 'preview-card';
    previewCard.style.position = 'relative';
    previewCard.style.width = '100px';
    previewCard.style.height = '100px';
    previewCard.style.borderRadius = '8px';
    previewCard.style.overflow = 'hidden';
    previewCard.style.border = '1px solid #ddd';

    const img = document.createElement('img');
    img.file = file;
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'cover';

    const reader = new FileReader();
    reader.onload = (e) => {
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);

    const removeBtn = document.createElement('button');
    removeBtn.innerHTML = '&times;';
    removeBtn.type = 'button'; // Prevent form submission
    removeBtn.style.position = 'absolute';
    removeBtn.style.top = '2px';
    removeBtn.style.right = '2px';
    removeBtn.style.background = 'rgba(255, 0, 0, 0.7)';
    removeBtn.style.color = 'white';
    removeBtn.style.border = 'none';
    removeBtn.style.borderRadius = '50%';
    removeBtn.style.width = '20px';
    removeBtn.style.height = '20px';
    removeBtn.style.cursor = 'pointer';
    removeBtn.style.display = 'flex';
    removeBtn.style.alignItems = 'center';
    removeBtn.style.justifyContent = 'center';
    removeBtn.style.fontSize = '14px';

    removeBtn.onclick = (e) => {
      e.stopPropagation(); // Prevent bubbling
      removeFile(file, previewCard);
    };

    previewCard.appendChild(img);
    previewCard.appendChild(removeBtn);
    previewContainer.appendChild(previewCard);
  }

  function removeFile(file, previewCard) {
    const newDt = new DataTransfer();
    for (let i = 0; i < dt.files.length; i++) {
      if (dt.files[i] !== file) {
        newDt.items.add(dt.files[i]);
      }
    }

    // Update the main DataTransfer object
    dt.items.clear();
    for (let i = 0; i < newDt.files.length; i++) {
      dt.items.add(newDt.files[i]);
    }

    updateInputFiles();
    updateInfo();
    previewContainer.removeChild(previewCard);
  }

  function updateInputFiles() {
    input.files = dt.files;
  }

  function updateInfo() {
    const count = dt.files.length;
    if (count > 0) {
      fileListInfo.textContent = `Выбрано файлов: ${count}`;
    } else {
      fileListInfo.textContent = '';
    }
  }
});
