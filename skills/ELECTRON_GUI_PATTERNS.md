# ELECTRON GUI PATTERNS - FRONTEND COMPONENT TEMPLATES

## Authority Level 11.0 | Collectibles Grading System Skill

---

## GRADE POPUP MODAL

### HTML TEMPLATE

```html
<div id="gradeModal" class="modal-overlay" style="display: none;">
  <div class="modal-content grade-modal">
    <button class="modal-close" onclick="closeGradeModal()">&times;</button>
    
    <div class="modal-header">
      <h2 id="modalTitle">Grading Results</h2>
      <span id="modalGrade" class="grade-badge">9.4</span>
    </div>
    
    <div class="modal-body">
      <!-- Comic Info Section -->
      <div class="info-section">
        <h3>Comic Information</h3>
        <div class="info-grid">
          <div class="info-item">
            <label>Title:</label>
            <span id="modalComicTitle">-</span>
          </div>
          <div class="info-item">
            <label>Issue:</label>
            <span id="modalIssue">-</span>
          </div>
          <div class="info-item">
            <label>Publisher:</label>
            <span id="modalPublisher">-</span>
          </div>
          <div class="info-item">
            <label>Year:</label>
            <span id="modalYear">-</span>
          </div>
          <div class="info-item">
            <label>Cover Date:</label>
            <span id="modalCoverDate">-</span>
          </div>
          <div class="info-item">
            <label>Cover Price:</label>
            <span id="modalCoverPrice">-</span>
          </div>
        </div>
      </div>
      
      <!-- AI Grades Section -->
      <div class="info-section">
        <h3>AI Consensus</h3>
        <div id="aiGradesContainer" class="ai-grades-grid">
          <!-- Populated by JavaScript -->
        </div>
        <div class="confidence-bar">
          <label>Confidence:</label>
          <div class="progress-bar">
            <div id="confidenceLevel" class="progress-fill"></div>
          </div>
          <span id="confidencePercent">85%</span>
        </div>
      </div>
      
      <!-- Defects Section -->
      <div class="info-section">
        <h3>Defects Detected</h3>
        <ul id="defectsList" class="defects-list">
          <!-- Populated by JavaScript -->
        </ul>
      </div>
      
      <!-- Key Issue Section -->
      <div id="keyIssueSection" class="info-section key-issue" style="display: none;">
        <h3>🔥 Key Issue</h3>
        <ul id="keyReasons" class="key-reasons">
          <!-- Populated by JavaScript -->
        </ul>
      </div>
      
      <!-- Pricing Section -->
      <div class="info-section">
        <h3>Estimated Value</h3>
        <div class="price-display">
          <span class="price-label">FMV at Grade:</span>
          <span id="modalFMV" class="price-value">$0.00</span>
        </div>
        <div id="priceRange" class="price-range">
          <span>Range: <span id="priceLow">$0</span> - <span id="priceHigh">$0</span></span>
        </div>
      </div>
    </div>
    
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeGradeModal()">Close</button>
      <button class="btn btn-primary" onclick="saveToCatalog()">Save to Catalog</button>
      <button class="btn btn-accent" onclick="regradeComic()">Re-Grade</button>
    </div>
  </div>
</div>
```

### CSS STYLES

```css
/* Modal Overlay */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

/* Modal Content */
.modal-content {
  background: #1a1a2e;
  border-radius: 12px;
  max-width: 700px;
  width: 90%;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  border: 1px solid #333;
}

.grade-modal {
  animation: modalSlideIn 0.3s ease;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Modal Close Button */
.modal-close {
  position: absolute;
  top: 15px;
  right: 20px;
  background: none;
  border: none;
  color: #888;
  font-size: 28px;
  cursor: pointer;
  transition: color 0.2s;
}

.modal-close:hover {
  color: #ff4757;
}

/* Modal Header */
.modal-header {
  padding: 20px 25px;
  border-bottom: 1px solid #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  margin: 0;
  color: #fff;
  font-size: 1.5rem;
}

.grade-badge {
  background: linear-gradient(135deg, #00d9ff, #00ff88);
  color: #000;
  padding: 8px 20px;
  border-radius: 20px;
  font-weight: bold;
  font-size: 1.3rem;
}

/* Info Sections */
.info-section {
  padding: 15px 25px;
  border-bottom: 1px solid #2a2a4a;
}

.info-section h3 {
  margin: 0 0 12px 0;
  color: #00d9ff;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.info-item {
  display: flex;
  gap: 8px;
}

.info-item label {
  color: #888;
  min-width: 90px;
}

.info-item span {
  color: #fff;
}

/* AI Grades Grid */
.ai-grades-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 15px;
}

.ai-grade-chip {
  background: #2a2a4a;
  padding: 8px 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-grade-chip .provider-icon {
  font-size: 1.2rem;
}

.ai-grade-chip .grade {
  font-weight: bold;
  color: #00ff88;
}

/* Confidence Bar */
.confidence-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #2a2a4a;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #00d9ff, #00ff88);
  transition: width 0.5s ease;
}

/* Defects List */
.defects-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.defects-list li {
  padding: 8px 12px;
  background: #2a2a4a;
  margin-bottom: 6px;
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.defects-list .severity {
  font-size: 0.8rem;
  padding: 2px 8px;
  border-radius: 4px;
}

.severity.minor { background: #ffc107; color: #000; }
.severity.moderate { background: #ff9800; color: #000; }
.severity.major { background: #f44336; color: #fff; }
.severity.severe { background: #9c27b0; color: #fff; }

/* Key Issue Section */
.key-issue {
  background: linear-gradient(135deg, #ff6b3520, #ff9f4320);
  border-left: 3px solid #ff6b35;
}

.key-reasons {
  list-style: none;
  padding: 0;
  margin: 0;
}

.key-reasons li {
  padding: 6px 0;
  color: #ffcc00;
}

.key-reasons li::before {
  content: "⭐ ";
}

/* Pricing Display */
.price-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.price-value {
  font-size: 1.8rem;
  font-weight: bold;
  color: #00ff88;
}

.price-range {
  color: #888;
  font-size: 0.9rem;
}

/* Modal Footer */
.modal-footer {
  padding: 20px 25px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* Buttons */
.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #00d9ff;
  color: #000;
}

.btn-primary:hover {
  background: #00b8d9;
  transform: translateY(-2px);
}

.btn-secondary {
  background: #2a2a4a;
  color: #fff;
}

.btn-secondary:hover {
  background: #3a3a5a;
}

.btn-accent {
  background: #ff6b35;
  color: #fff;
}

.btn-accent:hover {
  background: #ff8c5a;
}
```

### JAVASCRIPT FUNCTIONS

```javascript
// Open grade modal with data
function openGradeModal(gradingResult) {
  const modal = document.getElementById('gradeModal');
  
  // Populate basic info
  document.getElementById('modalTitle').textContent = 
    `${gradingResult.comic_info?.title || 'Unknown'} #${gradingResult.comic_info?.issue_number || '?'}`;
  document.getElementById('modalGrade').textContent = gradingResult.consensus_grade;
  
  // Comic info
  document.getElementById('modalComicTitle').textContent = gradingResult.comic_info?.title || '-';
  document.getElementById('modalIssue').textContent = gradingResult.comic_info?.issue_number || '-';
  document.getElementById('modalPublisher').textContent = gradingResult.comic_info?.publisher || '-';
  document.getElementById('modalYear').textContent = gradingResult.comic_info?.year || '-';
  document.getElementById('modalCoverDate').textContent = gradingResult.comic_info?.cover_date || '-';
  document.getElementById('modalCoverPrice').textContent = gradingResult.comic_info?.cover_price || '-';
  
  // AI Grades
  populateAIGrades(gradingResult.individual_grades);
  
  // Confidence
  const confidence = Math.round(gradingResult.confidence * 100);
  document.getElementById('confidenceLevel').style.width = `${confidence}%`;
  document.getElementById('confidencePercent').textContent = `${confidence}%`;
  
  // Defects
  populateDefects(gradingResult.defects);
  
  // Key Issue
  if (gradingResult.key_issue_info?.is_key_issue) {
    document.getElementById('keyIssueSection').style.display = 'block';
    populateKeyReasons(gradingResult.key_issue_info.key_reasons);
  } else {
    document.getElementById('keyIssueSection').style.display = 'none';
  }
  
  // Pricing
  document.getElementById('modalFMV').textContent = formatCurrency(gradingResult.estimated_value);
  
  modal.style.display = 'flex';
}

// Populate AI grades
function populateAIGrades(grades) {
  const container = document.getElementById('aiGradesContainer');
  container.innerHTML = '';
  
  const providerIcons = {
    'gemini': '💎',
    'grok': '🤖',
    'groq': '⚡',
    'openrouter': '🌐',
    'claude': '🧠'
  };
  
  for (const [provider, data] of Object.entries(grades || {})) {
    const chip = document.createElement('div');
    chip.className = 'ai-grade-chip';
    chip.innerHTML = `
      <span class="provider-icon">${providerIcons[provider] || '🔮'}</span>
      <span class="provider-name">${provider}</span>
      <span class="grade">${data.grade}</span>
    `;
    container.appendChild(chip);
  }
}

// Populate defects list
function populateDefects(defects) {
  const list = document.getElementById('defectsList');
  list.innerHTML = '';
  
  if (!defects || defects.length === 0) {
    list.innerHTML = '<li style="color: #00ff88;">No significant defects detected</li>';
    return;
  }
  
  defects.forEach(defect => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span>${defect.type}${defect.location ? ` (${defect.location})` : ''}</span>
      <span class="severity ${defect.severity}">${defect.severity}</span>
    `;
    list.appendChild(li);
  });
}

// Populate key reasons
function populateKeyReasons(reasons) {
  const list = document.getElementById('keyReasons');
  list.innerHTML = '';
  
  (reasons || []).forEach(reason => {
    const li = document.createElement('li');
    li.textContent = reason;
    list.appendChild(li);
  });
}

// Close modal
function closeGradeModal() {
  document.getElementById('gradeModal').style.display = 'none';
}

// Format currency
function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(value || 0);
}

// Close on overlay click
document.getElementById('gradeModal')?.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    closeGradeModal();
  }
});

// Close on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeGradeModal();
});
```

---

## COMIC CARD COMPONENT

### HTML TEMPLATE

```html
<div class="comic-card" data-id="${comic.id}" onclick="openComicDetails(${comic.id})">
  <div class="card-image">
    <img src="${comic.front_image || 'placeholder.png'}" alt="${comic.title}" loading="lazy">
    <div class="card-grade-badge">${comic.grade || 'RAW'}</div>
    ${comic.key_issue ? '<div class="key-badge">🔥 KEY</div>' : ''}
  </div>
  <div class="card-info">
    <h4 class="card-title">${escapeHtml(comic.title)}</h4>
    <p class="card-issue">#${comic.issue_number}</p>
    <p class="card-publisher">${comic.publisher}</p>
    <p class="card-value">${formatCurrency(comic.estimated_value)}</p>
  </div>
  <div class="card-actions">
    <button class="btn-icon" onclick="event.stopPropagation(); gradeComic(${comic.id})" title="Grade">
      📊
    </button>
    <button class="btn-icon" onclick="event.stopPropagation(); editComic(${comic.id})" title="Edit">
      ✏️
    </button>
    <button class="btn-icon" onclick="event.stopPropagation(); deleteComic(${comic.id})" title="Delete">
      🗑️
    </button>
  </div>
</div>
```

### CSS STYLES

```css
.comic-card {
  background: #1e1e2e;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.comic-card:hover {
  transform: translateY(-5px);
  border-color: #00d9ff;
  box-shadow: 0 10px 30px rgba(0, 217, 255, 0.2);
}

.card-image {
  position: relative;
  aspect-ratio: 0.65;
  overflow: hidden;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-grade-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.8);
  color: #00ff88;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.9rem;
}

.key-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  background: linear-gradient(135deg, #ff6b35, #ff9f43);
  color: #fff;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
}

.card-info {
  padding: 12px;
}

.card-title {
  margin: 0 0 4px 0;
  font-size: 1rem;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-issue {
  margin: 0;
  color: #00d9ff;
  font-weight: bold;
}

.card-publisher {
  margin: 4px 0;
  color: #888;
  font-size: 0.85rem;
}

.card-value {
  margin: 0;
  color: #00ff88;
  font-weight: bold;
  font-size: 1.1rem;
}

.card-actions {
  display: flex;
  justify-content: space-around;
  padding: 8px;
  background: #16162a;
  border-top: 1px solid #2a2a4a;
}

.btn-icon {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: #2a2a4a;
}
```

---

## WEBSOCKET EVENT HANDLERS

```javascript
// WebSocket connection manager
class GradingWebSocket {
  constructor(clientId) {
    this.clientId = clientId;
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.handlers = {};
  }
  
  connect() {
    this.socket = new WebSocket(`ws://localhost:8000/ws/${this.clientId}`);
    
    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connected');
    };
    
    this.socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
    
    this.socket.onclose = () => {
      console.log('WebSocket disconnected');
      this.emit('disconnected');
      this.attemptReconnect();
    };
    
    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    };
  }
  
  handleMessage(data) {
    switch (data.type) {
      case 'grade_complete':
        this.emit('gradeComplete', data.payload);
        showNotification('Grading complete!', 'success');
        openGradeModal(data.payload);
        break;
        
      case 'grade_progress':
        this.emit('gradeProgress', data.payload);
        updateProgressBar(data.payload.progress);
        break;
        
      case 'price_update':
        this.emit('priceUpdate', data.payload);
        updatePricing(data.payload);
        break;
        
      case 'batch_progress':
        this.emit('batchProgress', data.payload);
        updateBatchProgress(data.payload);
        break;
        
      case 'error':
        this.emit('error', data.payload);
        showNotification(data.payload.message, 'error');
        break;
        
      default:
        console.log('Unknown message type:', data.type);
    }
  }
  
  on(event, callback) {
    if (!this.handlers[event]) {
      this.handlers[event] = [];
    }
    this.handlers[event].push(callback);
  }
  
  emit(event, data) {
    const handlers = this.handlers[event] || [];
    handlers.forEach(handler => handler(data));
  }
  
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      console.log(`Reconnecting in ${delay}ms...`);
      setTimeout(() => this.connect(), delay);
    }
  }
  
  send(type, payload) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type, payload }));
    }
  }
}

// Initialize WebSocket
const ws = new GradingWebSocket('electron-client');
ws.connect();

// Event listeners
ws.on('gradeComplete', (result) => {
  refreshComicsList();
  updateStats();
});

ws.on('batchProgress', ({ completed, total, current }) => {
  const percent = Math.round((completed / total) * 100);
  document.getElementById('batchProgress').style.width = `${percent}%`;
  document.getElementById('batchStatus').textContent = `Grading ${current}... (${completed}/${total})`;
});
```

---

## UTILITY FUNCTIONS

```javascript
// HTML escape for XSS prevention
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Escape for HTML attributes
function escapeAttr(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// Show notification toast
function showNotification(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Debounce function
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
```

---

*Authority Level 11.0 | Electron GUI Patterns Skill*
