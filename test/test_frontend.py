"""Regression checks for the prompt editor's client-side behavior."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
WRITE_HTML = (ROOT / "frontend" / "write_prompt.html").read_text(encoding="utf-8")
WRITE_JS = (ROOT / "frontend" / "scripts" / "write_prompt_script.js").read_text(encoding="utf-8")


def test_manage_prompts_has_wildcard_search_control():
    html = (ROOT / "frontend" / "show_prompts.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "scripts" / "show_prompt_script.js").read_text(encoding="utf-8")
    assert 'id="promptWildcardSearch"' in html
    assert 'id="promptSearchBtn"' in html
    assert 'id="promptSearchBtn" aria-label="Search prompts" disabled' in html
    assert 'id="registerTagBtn"' not in html
    assert 'FILTER BY TAG' in html
    assert 'ASSIGN TAG TO PROMPT' in html
    assert 'Assign tag to prompt' not in html
    assert 'id="assignTagSelect"' in html
    assert 'class="prompt-select"' in js
    assert 'id="assignTagBtn"' not in html
    assert 'id="tagRegistryList"' not in html
    assert "promptWildcardSearch.value" in js
    assert "promptSearchBtn.addEventListener" in js
    assert "assignTagSelect.addEventListener('change'" in js
    assert "No prompt(s) selected for assign" in js
    assert "prompt-select:checked" in js
    assert "selectedIds.length" in js
    assert "tags.push(tag)" in js
    assert "promptSearchBtn.disabled = true" in js


def test_tag_management_panel_supports_filter_register_and_remove():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    tags_html = (ROOT / "frontend" / "manage_tags.html").read_text(encoding="utf-8")
    assert 'href="manage_tags.html"' in index_html
    assert index_html.index('href="show_prompts.html"') < index_html.index('href="manage_tags.html"')
    assert "wildcard" in tags_html
    assert "POST" in tags_html and "DELETE" in tags_html
    assert "/api/tags/details" in tags_html


def test_other_prompt_type_is_available_everywhere():
    write_html = (ROOT / "frontend" / "write_prompt.html").read_text(encoding="utf-8")
    show_html = (ROOT / "frontend" / "show_prompts.html").read_text(encoding="utf-8")
    write_js = (ROOT / "frontend" / "scripts" / "write_prompt_script.js").read_text(encoding="utf-8")
    show_js = (ROOT / "frontend" / "scripts" / "show_prompt_script.js").read_text(encoding="utf-8")
    assert 'value="other">Other' in write_html
    assert write_js.count("'Other'") >= 1
    assert show_html.count('value="Other"') >= 2
    assert 'value="Agent prompt"' in show_html
    assert "governanceTypeForTags" in show_js
    assert "requires the prompt type" in show_js
    assert "governance:user_instruction" in show_js


def test_versions_are_displayed():
    extension = (ROOT / "extensions" / "extension.py").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert '<span class="chip">v3.1</span>' in index_html
    assert 'class="stat-val">3</div><div class="stat-lbl">Prompt types' in index_html
    assert 'EXTENSION_VERSION = "1.0"' in extension
    assert "PromptHub extension v{EXTENSION_VERSION}" in extension


def test_homepage_shows_live_prompt_and_tag_counts():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'id="promptCount"' in index_html
    assert 'id="tagCount"' in index_html
    assert "fetch('/api/prompts')" in index_html
    assert "fetch('/api/tags/details')" in index_html


def test_save_panel_has_prompt_hint():
    assert 'id="promptHint"' in WRITE_HTML
    assert "firstLine.split" in WRITE_JS
    assert "slice(0, 4)" in WRITE_JS
    assert "promptHint.textContent" in WRITE_JS


def test_prompt_editor_can_change_prompt_type():
    show_html = (ROOT / "frontend" / "show_prompts.html").read_text(encoding="utf-8")
    show_js = (ROOT / "frontend" / "scripts" / "show_prompt_script.js").read_text(encoding="utf-8")
    assert 'id="editTypeSelect"' in show_html
    assert "editTypeSelect.value = currentItemType" in show_js
    assert "JSON.stringify({ body, type, tags })" in show_js
    assert "editTagsInput.value" in show_js


def test_prompt_editor_persists_and_clears_draft():
    assert "localStorage.setItem(DRAFT_KEY" in WRITE_JS
    assert "localStorage.getItem(DRAFT_KEY" in WRITE_JS
    assert "clearDraft();" in WRITE_JS
