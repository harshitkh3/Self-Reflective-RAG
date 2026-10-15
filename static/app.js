// ==========================================================================
// Self-Reflective RAG - Frontend Application Logic
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  const queryForm = document.getElementById('query-form');
  const queryInput = document.getElementById('query-input');
  const sendBtn = document.getElementById('send-btn');
  const chatMessages = document.getElementById('chat-messages');
  const heroWelcome = document.getElementById('hero-welcome');
  const clearChatBtn = document.getElementById('clear-chat-btn');
  const docList = document.getElementById('doc-list');
  const uploadZone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('file-input');
  const reindexBtn = document.getElementById('reindex-btn');
  const toast = document.getElementById('toast');

  let isGenerating = false;

  // Initialize
  loadDocuments();
  setupAutoResizeTextarea();
  setupSampleQueries();
  setupFileUpload();

  // ---------------------------------------------------------
  // Form Submission & Query Handling
  // ---------------------------------------------------------
  queryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query || isGenerating) return;

    await executeQuery(query);
  });

  // Enter to send, Shift+Enter for new line
  queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      queryForm.dispatchEvent(new Event('submit'));
    }
  });

  async function executeQuery(question) {
    isGenerating = true;
    sendBtn.disabled = true;
    queryInput.value = '';
    adjustTextareaHeight(queryInput);

    // Hide hero on first question
    if (heroWelcome) {
      heroWelcome.style.display = 'none';
    }

    // 1. Render User Message
    const messageRow = document.createElement('div');
    messageRow.className = 'message-row';

    const userBubble = document.createElement('div');
    userBubble.className = 'user-query-card';
    userBubble.textContent = question;
    messageRow.appendChild(userBubble);

    // 2. Render Thinking Placeholder with live steps simulation
    const thinkingCard = document.createElement('div');
    thinkingCard.className = 'thinking-card';
    thinkingCard.id = 'active-thinking-card';
    thinkingCard.innerHTML = `
      <div class="thinking-header">
        <div class="spinner"></div>
        <span id="thinking-step-text">Evaluating retrieval need (Decide Retrieval)...</span>
      </div>
      <div class="skeleton-line" style="width: 85%;"></div>
      <div class="skeleton-line" style="width: 65%;"></div>
      <div class="skeleton-line" style="width: 90%;"></div>
    `;
    messageRow.appendChild(thinkingCard);
    chatMessages.appendChild(messageRow);
    scrollToBottom();

    // Simulated progress text updates while waiting for backend
    const progressInterval = simulateProgress();

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to generate answer.');
      }

      const data = await response.json();
      renderSystemResponse(thinkingCard, data);

    } catch (err) {
      clearInterval(progressInterval);
      thinkingCard.innerHTML = `
        <div class="issup-banner issup-no_support">
          <span>❌ Execution Error: ${escapeHtml(err.message)}</span>
        </div>
      `;
    } finally {
      isGenerating = false;
      sendBtn.disabled = false;
      queryInput.focus();
      scrollToBottom();
    }
  }

  function simulateProgress() {
    const stepText = document.getElementById('thinking-step-text');
    const steps = [
      'Evaluating retrieval need (Decide Retrieval)...',
      'Searching vector knowledge base with Gemini Embeddings...',
      'Grading document relevance & filtering noise...',
      'Generating context-grounded response...',
      'Performing Self-Reflection (IsSUP Hallucination Check)...'
    ];
    let i = 0;
    return setInterval(() => {
      if (stepText && i < steps.length - 1) {
        i++;
        stepText.textContent = steps[i];
      }
    }, 2500);
  }

  // ---------------------------------------------------------
  // Render System Response with Stepper & Inspector
  // ---------------------------------------------------------
  function renderSystemResponse(container, data) {
    container.className = 'system-response-card';
    container.removeAttribute('id');

    // IsSUP Badge configuration
    const isSupConfig = {
      fully_supported: {
        label: '✨ Fully Supported (Zero Hallucination)',
        class: 'issup-fully_supported'
      },
      partially_supported: {
        label: '⚠️ Partially Supported (Abstracted / Inferred)',
        class: 'issup-partially_supported'
      },
      no_support: {
        label: '❌ No Support in Context',
        class: 'issup-no_support'
      }
    };
    const currentIsSup = isSupConfig[data.issup] || {
      label: `Verification: ${data.issup}`,
      class: 'issup-partially_supported'
    };

    // Stepper nodes
    const needRet = data.need_retrieval;
    const retCount = data.retrieved_docs_count;
    const relCount = data.relevant_docs_count;

    const stepperHtml = `
      <div class="pipeline-stepper">
        <div class="stepper-node done">
          <div class="node-icon-circle">💡</div>
          <span class="node-label">Decide</span>
          <span class="node-subtext">${needRet ? 'Retrieval: Yes' : 'Direct Answer'}</span>
        </div>
        <div class="stepper-arrow">➔</div>
        <div class="stepper-node ${needRet ? 'done' : 'skipped'}">
          <div class="node-icon-circle">📥</div>
          <span class="node-label">Retrieve</span>
          <span class="node-subtext">${needRet ? `${retCount} Docs` : 'Skipped'}</span>
        </div>
        <div class="stepper-arrow">➔</div>
        <div class="stepper-node ${needRet ? 'done' : 'skipped'}">
          <div class="node-icon-circle">⚖️</div>
          <span class="node-label">Filter</span>
          <span class="node-subtext">${needRet ? `${relCount} Relevant` : 'Skipped'}</span>
        </div>
        <div class="stepper-arrow">➔</div>
        <div class="stepper-node done">
          <div class="node-icon-circle">📝</div>
          <span class="node-label">Generate</span>
          <span class="node-subtext">Gemini 3.5</span>
        </div>
        <div class="stepper-arrow">➔</div>
        <div class="stepper-node done">
          <div class="node-icon-circle">🛡️</div>
          <span class="node-label">Reflect</span>
          <span class="node-subtext">${data.issup.replace('_', ' ')}</span>
        </div>
      </div>
    `;

    // Format Answer
    const formattedAnswer = formatMarkdownText(data.answer);

    // Build Evidence HTML
    let evidenceHtml = '';
    if (data.evidence && data.evidence.length > 0) {
      evidenceHtml = `
        <div class="inspector-section">
          <div class="inspector-section-title">Verified Grounding Evidence</div>
          <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 6px;">
            ${data.evidence.map(e => `
              <div class="chunk-card" style="border-left: 3px solid var(--success);">
                <div class="chunk-text">"${escapeHtml(e)}"</div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    // Build Chunks HTML
    const chunks = data.relevant_docs && data.relevant_docs.length > 0 ? data.relevant_docs : data.retrieved_docs;
    let chunksHtml = '';
    if (chunks && chunks.length > 0) {
      chunksHtml = `
        <div class="inspector-section">
          <div class="inspector-section-title">Retrieved Knowledge Chunks (${chunks.length})</div>
          <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 6px;">
            ${chunks.map((c, idx) => `
              <div class="chunk-card">
                <div class="chunk-header">
                  <span>📄 ${escapeHtml(c.source)}</span>
                  <span>Page ${c.page} · Chunk #${idx + 1}</span>
                </div>
                <div class="chunk-text">${escapeHtml(c.content)}</div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    const uniqueId = 'inspector-' + Math.random().toString(36).substr(2, 9);

    container.innerHTML = `
      <!-- Stepper Visual -->
      ${stepperHtml}

      <!-- IsSUP Badge -->
      <div class="issup-banner ${currentIsSup.class}">
        <span>${currentIsSup.label}</span>
        <span style="font-size: 11px; opacity: 0.85; font-family: var(--font-mono);">Self-RAG Guard</span>
      </div>

      <!-- Main Answer -->
      <div class="answer-body">
        ${formattedAnswer}
      </div>

      <!-- Footer Actions -->
      <div class="answer-actions">
        <button class="copy-btn" onclick="copyAnswerText(this)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          <span>Copy Answer</span>
        </button>

        ${chunks.length > 0 || data.evidence.length > 0 ? `
          <button class="toggle-inspector-btn" onclick="toggleInspector('${uniqueId}', this)">
            <span>View Retrieved Evidence (${chunks.length})</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>
        ` : ''}
      </div>

      <!-- Inspector Panel -->
      <div class="inspector-panel" id="${uniqueId}">
        ${evidenceHtml}
        ${chunksHtml}
      </div>
    `;

    scrollToBottom();
  }

  // ---------------------------------------------------------
  // Knowledge Base Documents API
  // ---------------------------------------------------------
  async function loadDocuments() {
    try {
      const res = await fetch('/api/documents');
      if (!res.ok) throw new Error('Failed to fetch documents');
      const data = await res.json();
      renderDocumentList(data.documents || []);
    } catch (err) {
      docList.innerHTML = `<div class="doc-empty">Could not load documents</div>`;
    }
  }

  function renderDocumentList(documents) {
    if (documents.length === 0) {
      docList.innerHTML = `<div class="doc-empty">No documents indexed yet. Upload a PDF above!</div>`;
      return;
    }

    docList.innerHTML = documents.map(doc => `
      <div class="doc-item">
        <div class="doc-info">
          <div class="doc-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
          </div>
          <div>
            <div class="doc-name" title="${escapeHtml(doc.name)}">${escapeHtml(doc.name)}</div>
            <div class="doc-size">${doc.size_kb} KB</div>
          </div>
        </div>
        <button class="doc-delete" onclick="deleteDocument('${escapeHtml(doc.name)}')" title="Delete Document">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    `).join('');
  }

  // File Upload
  function setupFileUpload() {
    uploadZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (file) await uploadFile(file);
      fileInput.value = '';
    });

    uploadZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
      uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', async (e) => {
      e.preventDefault();
      uploadZone.classList.remove('dragover');
      const file = e.dataTransfer.files[0];
      if (file) await uploadFile(file);
    });
  }

  async function uploadFile(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showToast('Only PDF files are supported.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    showToast(`Uploading & indexing ${file.name}...`);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Upload failed');
      }

      showToast(`Successfully added ${file.name} to knowledge base!`);
      await loadDocuments();
    } catch (err) {
      showToast(`Upload error: ${err.message}`);
    }
  }

  // Delete Document
  window.deleteDocument = async function(filename) {
    if (!confirm(`Are you sure you want to remove "${filename}" from the knowledge base?`)) return;

    try {
      const res = await fetch(`/api/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Failed to delete document');

      showToast(`Removed ${filename}. Knowledge base re-indexed!`);
      await loadDocuments();
    } catch (err) {
      showToast(`Delete error: ${err.message}`);
    }
  };

  // Re-index Button
  reindexBtn.addEventListener('click', async () => {
    reindexBtn.style.transform = 'rotate(360deg)';
    showToast('Re-indexing vector knowledge base...');
    try {
      const res = await fetch('/api/reindex', { method: 'POST' });
      if (res.ok) {
        showToast('Knowledge base successfully re-indexed!');
      }
    } catch (err) {
      showToast('Error re-indexing.');
    } finally {
      setTimeout(() => { reindexBtn.style.transform = 'none'; }, 600);
    }
  });

  // ---------------------------------------------------------
  // Helpers & UI Utilities
  // ---------------------------------------------------------
  function setupSampleQueries() {
    document.querySelectorAll('.query-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const query = chip.getAttribute('data-query');
        if (query) {
          queryInput.value = query;
          queryForm.dispatchEvent(new Event('submit'));
        }
      });
    });
  }

  clearChatBtn.addEventListener('click', () => {
    chatMessages.innerHTML = '';
    if (heroWelcome) {
      heroWelcome.style.display = 'flex';
      chatMessages.appendChild(heroWelcome);
    }
    showToast('Chat history cleared.');
  });

  function setupAutoResizeTextarea() {
    queryInput.addEventListener('input', () => adjustTextareaHeight(queryInput));
  }

  function adjustTextareaHeight(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }

  function scrollToBottom() {
    chatMessages.scrollTo({
      top: chatMessages.scrollHeight,
      behavior: 'smooth'
    });
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 3200);
  }

  window.toggleInspector = function(id, btn) {
    const panel = document.getElementById(id);
    if (!panel) return;
    const isOpen = panel.classList.toggle('open');
    const arrow = btn.querySelector('svg');
    if (arrow) {
      arrow.style.transform = isOpen ? 'rotate(180deg)' : 'none';
      arrow.style.transition = 'transform 0.2s ease';
    }
  };

  window.copyAnswerText = function(btn) {
    const card = btn.closest('.system-response-card');
    const answerBody = card.querySelector('.answer-body');
    if (!answerBody) return;

    navigator.clipboard.writeText(answerBody.innerText).then(() => {
      const originalText = btn.querySelector('span').textContent;
      btn.querySelector('span').textContent = 'Copied!';
      btn.style.color = 'var(--success)';
      setTimeout(() => {
        btn.querySelector('span').textContent = originalText;
        btn.style.color = '';
      }, 2000);
    });
  };

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatMarkdownText(text) {
    if (!text) return '<p>No answer generated.</p>';
    
    // Replace newlines with paragraph blocks
    const paragraphs = text.split(/\n\s*\n/).filter(p => p.trim().length > 0);
    return paragraphs.map(p => {
      let formatted = escapeHtml(p);
      // Bold text **word**
      formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      // Code blocks `code`
      formatted = formatted.replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); font-size: 13px;">$1</code>');
      return `<p>${formatted.replace(/\n/g, '<br>')}</p>`;
    }).join('');
  }
});
