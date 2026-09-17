const API_URL = "/api";

    let data = [];
    let currentItemId = null;
    let currentItemBody = "";
    let currentItemType = "System prompt";
    let currentItemTags = [];
    let tagColors = {};

    const listContainer = document.getElementById('listContainer');
    const filterTag = document.getElementById('filterTag');
    const filterCustomTag = document.getElementById('filterCustomTag');
    const assignTagSelect = document.getElementById('assignTagSelect');
    const filterCriticality = document.getElementById('filterCriticality');
    const filterCategory = document.getElementById('filterCategory');
    const searchInput = document.getElementById('searchInput');
    const promptWildcardSearch = document.getElementById('promptWildcardSearch');
    const promptSearchBtn = document.getElementById('promptSearchBtn');
    const totalCount = document.getElementById('totalCount');

    const modalOverlay = document.getElementById('modalOverlay');
    const modalContent = document.getElementById('modalContent');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    const modalBadges = document.getElementById('modalBadges');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const closeModalBtnBottom = document.getElementById('closeModalBtnBottom');
    const copyBtn = document.getElementById('copyBtn');
    const deleteBtn = document.getElementById('deleteBtn');
    const editBtn = document.getElementById('editBtn');

    const editModalOverlay = document.getElementById('editModalOverlay');
    const editModalContent = document.getElementById('editModalContent');
    const editTextarea = document.getElementById('editTextarea');
    const editTypeSelect = document.getElementById('editTypeSelect');
    const editTagsInput = document.getElementById('editTagsInput');
    const closeEditModalBtn = document.getElementById('closeEditModalBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    const updateBtn = document.getElementById('updateBtn');
    const toast = document.getElementById('toast');

    // ── API ──

    async function fetchPrompts() {
        const params = new URLSearchParams();
        const tagValue = filterTag.value;
        const customTagValue = filterCustomTag.value;
        const criticalityValue = filterCriticality.value;
        const catValue = filterCategory.value;
        const searchValue = promptWildcardSearch.value || searchInput.value;
        if (tagValue && tagValue !== 'all') params.append('tag', tagValue);
        if (customTagValue && customTagValue !== 'all') params.append('custom_tag', customTagValue);
        if (criticalityValue && criticalityValue !== 'all') params.append('criticality', criticalityValue);
        if (catValue && catValue !== 'all') params.append('category', catValue);
        if (searchValue) params.append('search', searchValue);

        try {
            const response = await fetch(`${API_URL}/prompts?${params}`);
            data = await response.json();
            renderList();
        } catch (error) {
            console.error('Error fetching prompts:', error);
            showErrorToast('Failed to load prompts');
        }
    }

    async function deletePromptAPI(id) {
        try {
            const response = await fetch(`${API_URL}/prompts/${id}`, { method: 'DELETE' });
            if (response.ok) {
                showToast('Prompt deleted');
                fetchPrompts();
            }
        } catch (error) {
            showErrorToast('Failed to delete prompt');
        }
    }

    async function updatePromptAPI(id, body, type, tags, refresh = true) {
        try {
            const response = await fetch(`${API_URL}/prompts/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ body, type, tags })
            });
            if (response.ok) {
                showToast('Prompt updated');
                closeEditModal();
                closeViewModal();
                if (refresh) fetchPrompts();
            } else {
                showErrorToast('Failed to update prompt');
            }
        } catch (error) {
            showErrorToast('Failed to update prompt');
        }
    }

    // ── UI ──

    function truncateText(text, wordCount = 9) {
        const words = text.split(' ');
        return words.length > wordCount ? words.slice(0, wordCount).join(' ') + '...' : text;
    }

    function tagStyle(tag) {
        const color = tagColors[tag.toLowerCase()];
        return color && /^#[0-9a-f]{3,8}$/i.test(color)
            ? ` style="color:${color};border-color:${color};"`
            : '';
    }

    function getBadgeClass(type, value) {
        if (type === 'favorite') return value === 'Favorite' ? 'badge-fav' : 'badge-nfav';
        if (type === 'type') return value === 'User prompt' ? 'badge-user' : 'badge-sys';
        if (type === 'criticality') return `badge-criticality-${value}`;
        return '';
    }

    function renderList() {
        totalCount.innerText = data.length;
        listContainer.innerHTML = '';

        if (data.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fa-regular fa-folder-open"></i>
                    <p>No prompts found matching your criteria.</p>
                </div>`;
            return;
        }

        data.forEach(item => {
            const card = document.createElement('div');
            card.className = 'prompt-card';
            card.onclick = () => openModal(item);

            const iconClass = item.type === 'User prompt'
                ? 'fa-user' : 'fa-robot';
            const iconColor = item.type === 'User prompt'
                ? 'color:var(--blue)' : 'color:var(--purple)';

            card.innerHTML = `
                <div class="card-inner">
                    <div class="card-left">
                        <div class="card-icon">
                            <i class="fa-solid ${iconClass}" style="${iconColor};font-size:14px;"></i>
                            <label class="prompt-select-wrap" title="Select prompt" onclick="event.stopPropagation()">
                                <input type="checkbox" class="prompt-select" data-prompt-id="${item.id}" aria-label="Select ${escapeHtml(item.title)}">
                            </label>
                        </div>
                        <div class="card-text">
                            <div class="card-title">${item.title}</div>
                            <div class="card-preview">${truncateText(item.body)}</div>
                            <div class="card-date">Updated ${escapeHtml(item.updated_at || item.date)}</div>
                        </div>
                    </div>
                    <div class="card-badges">
                        <span class="badge ${getBadgeClass('favorite', item.favorite)}">
                            ${item.favorite === 'Favorite' ? '★ ' : ''}${item.favorite}
                        </span>
                        <span class="badge ${getBadgeClass('type', item.type)}">${item.type}</span>
                        <span class="badge ${getBadgeClass('criticality', item.criticality)}">${item.criticality}</span>
                        ${(item.tags || []).filter(t => !/^criticality:/i.test(t)).map(t => `<span class="badge badge-tag"${tagStyle(t)}>${escapeHtml(t)}</span>`).join('')}
                    </div>
                </div>`;
            listContainer.appendChild(card);
        });
    }

    function openModal(item) {
        currentItemId = item.id;
        currentItemBody = item.body;
        currentItemType = item.type;
        currentItemTags = [...(item.tags || [])];
        editTagsInput.value = currentItemTags.join(', ');
        modalTitle.innerText = item.title;
        modalBody.innerText = item.body;

        const customTagBadges = (item.tags || []).filter(t => !/^criticality:/i.test(t)).map(t => `<span class="badge badge-tag"${tagStyle(t)}>${escapeHtml(t)}</span>`).join('');
        const criticalityBadge = `<span class="badge ${getBadgeClass('criticality', item.criticality)}">${item.criticality}</span>`;
        modalBadges.innerHTML = `
            <span class="badge ${getBadgeClass('favorite', item.favorite)}">${item.favorite}</span>
            <span class="badge ${getBadgeClass('type', item.type)}">${item.type}</span>
            ${criticalityBadge}
            ${customTagBadges}
            <span class="modal-date"><i class="fa-regular fa-calendar" style="margin-right:4px;"></i>Created ${item.date}</span>
            <span class="modal-date"><i class="fa-regular fa-clock" style="margin-right:4px;"></i>Updated ${item.updated_at || item.date}</span>`;

        modalOverlay.classList.remove('hidden');
        setTimeout(() => {
            modalOverlay.classList.remove('opacity-0');
            modalContent.classList.remove('scale-95');
            modalContent.classList.add('scale-100');
        }, 10);
    }

    function closeViewModal() {
        modalOverlay.classList.add('opacity-0');
        modalContent.classList.remove('scale-100');
        modalContent.classList.add('scale-95');
        setTimeout(() => {
            modalOverlay.classList.add('hidden');
            currentItemId = null;
            currentItemBody = "";
            currentItemType = "System prompt";
            currentItemTags = [];
        }, 250);
    }

    function openEditModal() {
        editTextarea.value = currentItemBody;
        editTypeSelect.value = currentItemType;
        editModalOverlay.classList.remove('hidden');
        setTimeout(() => {
            editModalOverlay.classList.remove('opacity-0');
            editModalContent.classList.remove('scale-95');
            editModalContent.classList.add('scale-100');
            editTextarea.focus();
        }, 10);
    }

    function closeEditModal() {
        editModalOverlay.classList.add('opacity-0');
        editModalContent.classList.remove('scale-100');
        editModalContent.classList.add('scale-95');
        setTimeout(() => { editModalOverlay.classList.add('hidden'); }, 250);
    }

    function copyToClipboard() {
        navigator.clipboard.writeText(modalBody.innerText).then(() => showToast('Copied to clipboard!'));
    }

    function governanceTypeForTags(tags) {
        if (tags.some(tag => tag.toLowerCase() === 'governance:system_instruction')) return 'System prompt';
        if (tags.some(tag => tag.toLowerCase() === 'governance:agent_instruction')) return 'Agent prompt';
        if (tags.some(tag => tag.toLowerCase() === 'governance:user_instruction')) return 'User prompt';
        return null;
    }

    function handleUpdate() {
        const updatedBody = editTextarea.value.trim();
        if (!updatedBody) { showErrorToast('Prompt body cannot be empty'); return; }
        const tags = editTagsInput.value.split(',').map(tag => tag.trim().replace(/^#+/, '')).filter(Boolean);
        const governanceType = governanceTypeForTags(tags);
        let type = editTypeSelect.value;
        if (governanceType && type !== governanceType && !confirm(`This governance tag requires the prompt type “${governanceType}”. Adjust the type automatically?`)) return;
        if (governanceType) type = governanceType;
        if (currentItemId !== null) updatePromptAPI(currentItemId, updatedBody, type, tags);
    }

    let toastTimer;
    function showToast(message = 'Done!') {
        const span = toast.querySelector('span');
        const icon = toast.querySelector('i');
        span.textContent = message;
        toast.classList.remove('error');
        icon.className = 'fa-solid fa-circle-check';
        icon.style.color = 'var(--green)';
        toast.style.borderColor = 'var(--green)';
        toast.classList.add('visible');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toast.classList.remove('visible'), 3000);
    }

    function showErrorToast(message) {
        const span = toast.querySelector('span');
        const icon = toast.querySelector('i');
        span.textContent = message;
        toast.classList.add('error');
        icon.className = 'fa-solid fa-circle-xmark';
        icon.style.color = 'var(--red)';
        toast.style.borderColor = 'var(--red)';
        toast.classList.add('visible');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toast.classList.remove('visible'), 3000);
    }

    // ── Events ──
    async function loadTagOptions() {
        try {
            const response = await fetch(`${API_URL}/tags/details`);
            const details = await response.json();
            tagColors = Object.fromEntries(details.map(item => [item.name.toLowerCase(), item.color]));
            const tags = details.map(item => item.name);
            const current = filterCustomTag.value || 'all';
            filterCustomTag.innerHTML = '<option value="all">All Tags</option>' +
                details.map(item => `<option value="${escapeHtml(item.name)}"${tagStyle(item.name)}>${escapeHtml(item.name)}</option>`).join('');
            filterCustomTag.value = tags.some(t => t === current) ? current : 'all';
            assignTagSelect.innerHTML = '<option value="">Select a tag</option>' +
                details.map(item => `<option value="${escapeHtml(item.name)}">${escapeHtml(item.name)}</option>`).join('');
        } catch (error) {
            console.error('Error loading tags:', error);
        }
    }

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    filterTag.addEventListener('change', fetchPrompts);
    filterCustomTag.addEventListener('change', fetchPrompts);
    assignTagSelect.addEventListener('change', async () => {
        const tag = assignTagSelect.value;
        const selectedIds = [...document.querySelectorAll('.prompt-select:checked')]
            .map(input => Number(input.dataset.promptId));
        if (!selectedIds.length) return showErrorToast('No prompt(s) selected for assign');
        if (!tag) return showErrorToast('Select a tag to assign');

        const governanceTypes = new Set();
        for (const id of selectedIds) {
            const item = data.find(prompt => prompt.id === id);
            if (!item) continue;
            const tags = [...(item.tags || [])];
            if (!tags.some(itemTag => itemTag.toLowerCase() === tag.toLowerCase())) tags.push(tag);
            const governanceType = governanceTypeForTags(tags);
            if (governanceType && item.type !== governanceType) governanceTypes.add(governanceType);
        }
        for (const governanceType of governanceTypes) {
            if (!confirm(`This governance tag requires the prompt type “${governanceType}”. Adjust selected prompt types automatically?`)) {
                assignTagSelect.value = '';
                return;
            }
        }

        for (const id of selectedIds) {
            const item = data.find(prompt => prompt.id === id);
            if (!item) continue;
            const tags = [...(item.tags || [])];
            if (!tags.some(itemTag => itemTag.toLowerCase() === tag.toLowerCase())) tags.push(tag);
            const governanceType = governanceTypeForTags(tags);
            await updatePromptAPI(id, item.body, governanceType || item.type, tags, false);
        }
        document.querySelectorAll('.prompt-select:checked').forEach(input => { input.checked = false; });
        assignTagSelect.value = '';
        await fetchPrompts();
    });
    filterCriticality.addEventListener('change', fetchPrompts);
    filterCategory.addEventListener('change', fetchPrompts);
    searchInput.addEventListener('input', debounce(fetchPrompts, 300));
    function setSearchButtonState() {
        promptSearchBtn.disabled = !promptWildcardSearch.value.trim();
    }
    promptWildcardSearch.addEventListener('input', setSearchButtonState);
    promptWildcardSearch.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !promptSearchBtn.disabled) promptSearchBtn.click();
    });
    promptSearchBtn.addEventListener('click', async () => {
        if (promptSearchBtn.disabled) return;
        promptSearchBtn.disabled = true;
        await fetchPrompts();
    });
    closeModalBtn.addEventListener('click', closeViewModal);
    //closeModalBtnBottom.addEventListener('click', closeViewModal);
    copyBtn.addEventListener('click', copyToClipboard);
    deleteBtn.addEventListener('click', () => { if (currentItemId !== null) { deletePromptAPI(currentItemId); closeViewModal(); } });
    editBtn.addEventListener('click', openEditModal);
    closeEditModalBtn.addEventListener('click', closeEditModal);
    cancelEditBtn.addEventListener('click', closeEditModal);
    updateBtn.addEventListener('click', handleUpdate);

    modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeViewModal(); });
    editModalOverlay.addEventListener('click', e => { if (e.target === editModalOverlay) closeEditModal(); });

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            if (!editModalOverlay.classList.contains('hidden')) closeEditModal();
            else if (!modalOverlay.classList.contains('hidden')) closeViewModal();
        }
    });

    function debounce(func, wait) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    }

    loadTagOptions().then(fetchPrompts);