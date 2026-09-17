document.addEventListener('DOMContentLoaded', function () {
        const API_URL = "/api";

        const textarea = document.getElementById('message');
        const saveButton = document.getElementById('save_button');
        const saveModal = document.getElementById('saveModal');
        const saveForm = document.getElementById('saveForm');
        const cancelButton = document.getElementById('cancelButton');
        const promptNameInput = document.getElementById('promptName');
        const promptTagSelect = document.getElementById('promptTag');
        const promptCategorySelect = document.getElementById('promptCategory');
        const promptCriticalitySelect = document.getElementById('promptCriticality');
        const promptTagsInput = document.getElementById('promptTags');
        const promptHint = document.getElementById('promptHint');
        const tagChips = document.getElementById('tagChips');
        const toast = document.getElementById('toast');
        let customTags = [];
        const charStatus = document.getElementById('charStatus');
        const wordStatus = document.getElementById('wordStatus');
        const positionStatus = document.getElementById('positionStatus');
        const lineNumbers = document.getElementById('lineNumbers');
        const modifiedDot = document.getElementById('modifiedDot');
        const fileLabel = document.getElementById('fileLabel');
        const minimapContent = document.getElementById('minimapContent');
        const DRAFT_KEY = 'prompthub.prompt-draft.v1';

        function saveDraft() {
            try {
                localStorage.setItem(DRAFT_KEY, JSON.stringify({
                    body: textarea.value, title: promptNameInput.value,
                    favorite: promptTagSelect.value, category: promptCategorySelect.value,
                    criticality: promptCriticalitySelect.value, pendingTag: promptTagsInput.value,
                    tags: customTags
                }));
            } catch (error) { console.warn('Unable to save local draft:', error); }
        }

        function clearDraft() { localStorage.removeItem(DRAFT_KEY); }

        function restoreDraft() {
            try {
                const draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null');
                if (!draft) return false;
                textarea.value = draft.body || '';
                promptNameInput.value = draft.title || '';
                promptTagSelect.value = draft.favorite || promptTagSelect.value;
                promptCategorySelect.value = draft.category || promptCategorySelect.value;
                promptCriticalitySelect.value = draft.criticality || promptCriticalitySelect.value;
                promptTagsInput.value = draft.pendingTag || '';
                customTags = Array.isArray(draft.tags) ? draft.tags : [];
                renderTagChips();
                return Boolean(textarea.value || promptNameInput.value || customTags.length);
            } catch (error) { clearDraft(); return false; }
        }

        function updateLineNumbers() {
            const lines = textarea.value.split('\n');
            let html = '';
            for (let i = 1; i <= Math.max(lines.length, 1); i++) {
                html += `<div class="ln">${i}</div>`;
            }
            lineNumbers.innerHTML = html;
        }

        function updateMinimap() {
            const lines = textarea.value.split('\n');
            let html = '';
            lines.forEach(line => {
                const filled = line.trim().length > 0;
                const w = Math.min(100, Math.max(20, line.length * 3));
                html += `<div class="minimap-line${filled ? ' filled' : ''}" style="width:${w}%"></div>`;
            });
            minimapContent.innerHTML = html;
        }

        function updateStats() {
            const val = textarea.value;
            const chars = val.length;
            const words = val.trim() === '' ? 0 : val.trim().split(/\s+/).length;
            charStatus.textContent = chars.toLocaleString() + ' chars';
            wordStatus.textContent = words.toLocaleString() + ' words';

            if (chars > 0) {
                modifiedDot.style.display = 'block';
                fileLabel.textContent = 'Unsaved changes';
                fileLabel.style.color = 'var(--orange)';
            } else {
                modifiedDot.style.display = 'none';
                fileLabel.textContent = 'No changes';
                fileLabel.style.color = 'var(--text-3)';
            }
        }

        function updatePosition() {
            const text = textarea.value;
            const pos = textarea.selectionStart;
            const before = text.substring(0, pos);
            const lines = before.split('\n');
            const ln = lines.length;
            const col = lines[lines.length - 1].length + 1;
            positionStatus.textContent = `Ln ${ln}, Col ${col}`;
        }

        textarea.addEventListener('input', () => { updateLineNumbers(); updateStats(); updateMinimap(); saveDraft(); });
        textarea.addEventListener('keyup', updatePosition);
        textarea.addEventListener('click', updatePosition);
        textarea.addEventListener('mouseup', updatePosition);

        textarea.addEventListener('keydown', function (e) {
            if (e.key === 'Tab') {
                e.preventDefault();
                const start = this.selectionStart;
                const end = this.selectionEnd;
                this.value = this.value.substring(0, start) + '    ' + this.value.substring(end);
                this.selectionStart = this.selectionEnd = start + 4;
                updateLineNumbers(); updateStats(); updateMinimap(); saveDraft();
            }
            if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                e.preventDefault();
                openModal();
            }
        });

        function openModal() {
            const content = textarea.value.trim();
            if (!content) { shakeButton(); return; }
            const firstLine = content.split(/\r?\n/)[0].trim();
            const words = firstLine.split(/\s+/).slice(0, 4).join(' ');
            promptHint.textContent = `${words}${firstLine.split(/\s+/).length > 4 ? '...' : ''}`;
            saveModal.classList.add('active');
            setTimeout(() => promptNameInput.focus(), 100);
        }

        function renderTagChips() {
            tagChips.innerHTML = customTags.map((tag, i) =>
                `<span class="tag-chip">${escapeHtml(tag)}<button type="button" class="tag-chip-x" data-index="${i}" aria-label="Remove tag">×</button></span>`
            ).join('');
        }

        function escapeHtml(s) {
            return String(s)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#39;");
        }

        function addTag(raw) {
            const name = raw.trim().replace(/^#+/, '');
            if (!name) return;
            if (customTags.some(t => t.toLowerCase() === name.toLowerCase())) return;
            customTags.push(name);
            renderTagChips();
            saveDraft();
        }

        function closeModal() {
            saveModal.classList.remove('active');
            saveForm.reset();
            customTags = [];
            renderTagChips();
        }

        function shakeButton() {
            saveButton.style.transform = 'translateX(-3px)';
            setTimeout(() => { saveButton.style.transform = 'translateX(3px)'; }, 60);
            setTimeout(() => { saveButton.style.transform = 'translateX(-2px)'; }, 120);
            setTimeout(() => { saveButton.style.transform = 'translateX(0)'; }, 180);
        }

        saveButton.addEventListener('click', openModal);
        cancelButton.addEventListener('click', closeModal);
        saveModal.addEventListener('click', e => { if (e.target === saveModal) closeModal(); });
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

        tagChips.addEventListener('click', e => {
            const btn = e.target.closest('.tag-chip-x');
            if (!btn) return;
            customTags.splice(Number(btn.dataset.index), 1);
            renderTagChips();
            saveDraft();
        });

        promptTagsInput.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                addTag(promptTagsInput.value);
                promptTagsInput.value = '';
            } else if (e.key === 'Backspace' && !promptTagsInput.value && customTags.length) {
                customTags.pop();
                renderTagChips();
                saveDraft();
            }
        });
        promptTagsInput.addEventListener('input', saveDraft);
        promptTagsInput.addEventListener('blur', () => {
            if (promptTagsInput.value.trim()) {
                addTag(promptTagsInput.value);
                promptTagsInput.value = '';
                saveDraft();
            }
        });
        [promptNameInput, promptTagSelect, promptCategorySelect, promptCriticalitySelect]
            .forEach(input => input.addEventListener('input', saveDraft));
        window.addEventListener('beforeunload', saveDraft);

        saveForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            if (promptTagsInput.value.trim()) {
                addTag(promptTagsInput.value);
                promptTagsInput.value = '';
            }

            // Keep criticality machine-readable while preserving the user's tags.
            const tags = customTags.filter(tag => !/^criticality:/i.test(tag));
            tags.push(`criticality:${promptCriticalitySelect.value}`);
            const promptData = {
                title: promptNameInput.value.trim(),
                body: textarea.value.trim(),
                favorite: promptTagSelect.value === 'favorite' ? 'Favorite' : 'Not favorite',
                type: promptCategorySelect.value === 'system' ? 'System prompt' :
                    promptCategorySelect.value === 'user' ? 'User prompt' : 'Other',
                tags
            };

            const originalHTML = saveButton.innerHTML;
            saveButton.innerHTML = `
                <svg class="spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10" stroke-dasharray="31.4" stroke-dashoffset="10"/>
                </svg>
                Saving...`;
            saveButton.disabled = true;

            try {
                const response = await fetch(`${API_URL}/prompts`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(promptData)
                });

                if (response.ok) {
                    clearDraft();
                    closeModal();
                    textarea.value = '';
                    saveForm.reset();
                    customTags = [];
                    renderTagChips();
                    updateLineNumbers(); updateStats(); updateMinimap();

                    toast.querySelector('span').textContent = `"${promptData.title}" saved!`;
                    toast.classList.add('show');
                    setTimeout(() => toast.classList.remove('show'), 3200);

                    fileLabel.textContent = 'Saved';
                    fileLabel.style.color = 'var(--green)';
                    modifiedDot.style.display = 'none';
                    setTimeout(() => {
                        fileLabel.textContent = 'No changes';
                        fileLabel.style.color = 'var(--text-3)';
                    }, 3000);
                } else {
                    throw new Error('Failed to save');
                }
            } catch (error) {
                console.error('Error saving:', error);
                alert('Failed to save prompt. Please try again.');
            } finally {
                saveButton.innerHTML = originalHTML;
                saveButton.disabled = false;
            }
        });

        const draftRestored = restoreDraft();
        updateLineNumbers(); updateStats(); updateMinimap();
        if (draftRestored) {
            fileLabel.textContent = 'Draft restored';
            fileLabel.style.color = 'var(--orange)';
        }
    });