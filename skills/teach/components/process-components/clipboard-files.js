// Preserve picker, paste, and drop selections in one in-memory list.
export function bindFileCollection({root, input, dropZone, output, maxFiles = 5, render}) {
  let selectedFiles = [];

  function update() {
    output.textContent = selectedFiles.map(file => file.name).join(', ');
    render?.(selectedFiles.map((file, index) => ({file, index, remove: () => remove(index)})));
  }

  function remove(index) {
    selectedFiles.splice(index, 1);
    update();
  }

  function addFiles(files) {
    for (const file of files) {
      if (selectedFiles.length >= maxFiles) break;
      if (!selectedFiles.some(existing =>
        existing.name === file.name &&
        existing.size === file.size &&
        existing.lastModified === file.lastModified
      )) selectedFiles.push(file);
    }
    update();
    input.value = '';
  }

  input.addEventListener('change', () => addFiles(input.files));
  root.addEventListener('paste', event => {
    const files = [...(event.clipboardData?.items || [])]
      .filter(item => item.kind === 'file')
      .map(item => item.getAsFile())
      .filter(Boolean);
    if (files.length) {
      event.preventDefault();
      addFiles(files);
    }
  });
  dropZone.addEventListener('dragover', event => event.preventDefault());
  dropZone.addEventListener('drop', event => {
    event.preventDefault();
    addFiles(event.dataTransfer.files);
  });

  return {
    appendTo(formData, field = 'files') {
      selectedFiles.forEach(file => formData.append(field, file, file.name));
    },
    clear() {
      selectedFiles = [];
      update();
    },
    remove,
    files() {
      return [...selectedFiles];
    },
  };
}

// Track persisted evidence separately from pending browser Files. Removal is explicit and
// affects only the next evaluation manifest; it never deletes the stored historical file.
export function createEvidenceSelection(evidence = []) {
  const kept = new Set(evidence.map(item => String(item.id)));
  const removed = new Set();
  return {
    remove(id) { kept.delete(String(id)); removed.add(String(id)); },
    restore(id) { removed.delete(String(id)); kept.add(String(id)); },
    keptIds() { return [...kept]; },
    removedIds() { return [...removed]; },
    appendTo(formData) {
      formData.set('kept_evidence_ids', JSON.stringify([...kept]));
      formData.set('removed_evidence_ids', JSON.stringify([...removed]));
    },
  };
}
