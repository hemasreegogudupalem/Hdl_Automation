/**
 * Oracle Fusion Cloud HCM - HDL Automation
 * Frontend Application Controller (Vibrant Enterprise Light Edition)
 * Zero Backend Modification: Interacts with unmodified backend services.
 */

// Application State
const state = {
  currentTab: 'upload',
  selectedInput: 'input/saudi_employee_data.xlsx',
  selectedTemplate: 'Worker',
  inputs: [],
  templates: [],
  dbStatus: null,
  detectedDefaults: {},
  generationResult: null,
  isGenerating: false,

  // Data Grid state for Upload Tab
  dataGrid: {
    page: 1,
    pageSize: 15,
    search: '',
    totalRows: 0,
    totalPages: 1,
    columns: [],
    rows: []
  },

  // Mappings state
  mappings: {
    filter: 'all',
    search: '',
    data: []
  },

  // Outputs state
  outputs: {
    files: [],
    reports: [],
    activeFile: null,
    activeCategory: 'output',
    activeRawText: '',
  }
};

// 3D Tab Themes for Sidebar Navigation
const tabThemes = {
  upload: {
    activeClass: 'bg-emerald-50 text-emerald-950 border-emerald-300 border-b-2 border-b-emerald-400 shadow-xs font-bold',
    iconBg: 'bg-emerald-100 text-emerald-700 shadow-2xs',
    dotColor: 'bg-emerald-500 shadow-xs'
  },
  generator: {
    activeClass: 'bg-indigo-50 text-indigo-950 border-indigo-300 border-b-2 border-b-indigo-400 shadow-xs font-bold',
    iconBg: 'bg-indigo-100 text-indigo-700 shadow-2xs',
    dotColor: 'bg-indigo-500 shadow-xs'
  },
  mappings: {
    activeClass: 'bg-amber-50 text-amber-950 border-amber-300 border-b-2 border-b-amber-400 shadow-xs font-bold',
    iconBg: 'bg-amber-100 text-amber-700 shadow-2xs',
    dotColor: 'bg-amber-500 shadow-xs'
  },
  outputs: {
    activeClass: 'bg-violet-50 text-violet-950 border-violet-300 border-b-2 border-b-violet-400 shadow-xs font-bold',
    iconBg: 'bg-violet-100 text-violet-700 shadow-2xs',
    dotColor: 'bg-violet-500 shadow-xs'
  },
  database: {
    activeClass: 'bg-teal-50 text-teal-950 border-teal-300 border-b-2 border-b-teal-400 shadow-xs font-bold',
    iconBg: 'bg-teal-100 text-teal-700 shadow-2xs',
    dotColor: 'bg-teal-500 shadow-xs'
  }
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setupFileUpload();
  setupEventListeners();

  // Load initial backend status and assets
  await refreshSystemStatus();
  await loadTemplates();
  await loadInputFiles();
  await triggerAutoDetect();
  await loadOutputFiles();
});

// Toast Notifications (Clean Enterprise Light UI, No Emojis)
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const borderClass =
    type === 'success' ? 'border-emerald-300 text-emerald-950 bg-emerald-50/90' :
    type === 'error' ? 'border-rose-300 text-rose-950 bg-rose-50/90' :
    type === 'warning' ? 'border-amber-300 text-amber-950 bg-amber-50/90' :
    'border-indigo-300 text-slate-800 bg-white';

  const dotClass =
    type === 'success' ? 'bg-emerald-600' :
    type === 'error' ? 'bg-rose-600' :
    type === 'warning' ? 'bg-amber-600' :
    'bg-indigo-600';

  toast.className = `toast ${borderClass}`;
  toast.innerHTML = `
    <span class="w-2 h-2 rounded-full ${dotClass} shrink-0"></span>
    <div class="flex-1 text-xs font-semibold">${escapeHtml(message)}</div>
    <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-slate-700 text-sm font-bold ml-2">&times;</button>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'all 0.25s ease-out';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

// System Status and DB Check
async function refreshSystemStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    state.dbStatus = data.database;
    renderStatusBadge(data.database);
    return data;
  } catch (err) {
    renderStatusBadge({ status: 'offline', error: err.message });
  }
}

function renderStatusBadge(db) {
  const badge = document.getElementById('mysql-status-badge');
  const details = document.getElementById('mysql-status-text');
  const clientBadge = document.getElementById('client-badge-text');
  if (!badge) return;

  if (db && db.status === 'connected') {
    badge.className = 'w-2 h-2 rounded-full bg-emerald-500 live-dot inline-block';
    details.innerHTML = `MySQL: <span class="font-bold text-emerald-900">${db.database}</span> @ ${db.host}:${db.port}`;
    if (clientBadge) {
      clientBadge.textContent = `Client: ${db.active_client || 'Active'} (${db.source_system_owner || 'GRISMO'})`;
    }
  } else {
    badge.className = 'w-2 h-2 rounded-full bg-rose-600 inline-block';
    details.innerHTML = `<span class="text-rose-700 font-bold">MySQL Offline</span>`;
    if (clientBadge) {
      clientBadge.textContent = 'Client: Offline';
    }
  }
}

// Tab Navigation: upload, generator, mappings, outputs, database
function setupNavigation() {
  const navButtons = document.querySelectorAll('.nav-tab-btn');
  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });
}

function switchTab(tabName) {
  state.currentTab = tabName;
  document.querySelectorAll('.tab-view').forEach(view => {
    view.classList.add('hidden');
  });

  const activeView = document.getElementById(`view-${tabName}`);
  if (activeView) activeView.classList.remove('hidden');

  document.querySelectorAll('.nav-tab-btn').forEach(btn => {
    const t = btn.getAttribute('data-tab');
    const theme = tabThemes[t] || tabThemes.generator;
    const iconSpan = btn.querySelector('span:first-child');
    let indicator = btn.querySelector('.tab-active-dot');

    if (t === tabName) {
      btn.className = `nav-tab-btn w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-bold transition-all border ${theme.activeClass}`;
      if (iconSpan) iconSpan.className = `w-6 h-6 rounded-lg ${theme.iconBg} flex items-center justify-center`;
      if (!indicator) {
        indicator = document.createElement('span');
        indicator.className = `tab-active-dot w-2 h-2 rounded-full ${theme.dotColor}`;
        btn.appendChild(indicator);
      } else {
        indicator.className = `tab-active-dot w-2 h-2 rounded-full ${theme.dotColor}`;
      }
    } else {
      btn.className = `nav-tab-btn w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all border border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50`;
      if (iconSpan) iconSpan.className = 'w-6 h-6 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center';
      if (indicator) indicator.remove();
    }
  });

  // Lazy tab data loading
  if (tabName === 'upload') loadDataGrid();
  if (tabName === 'mappings') loadFieldMappings();
  if (tabName === 'database') loadDatabaseSchema();
  if (tabName === 'outputs') loadOutputFiles();
}

// Load Templates from API
async function loadTemplates() {
  try {
    const res = await fetch('/api/templates');
    const templates = await res.json();
    state.templates = templates;
    renderTemplateOptions(templates);
    renderSchemaTemplateSelect(templates);
    updateTemplateBadges();
  } catch (err) {
    showToast('Failed to load templates: ' + err.message, 'error');
  }
}

function renderSchemaTemplateSelect(templates) {
  const select = document.getElementById('db-template-select');
  if (!select) return;
  select.innerHTML = templates.map(t => `
    <option value="${t.template_name}" ${t.template_name === state.selectedTemplate ? 'selected' : ''}>
      ${t.template_name} (${t.objects_count} objects)
    </option>
  `).join('');

  select.onchange = (e) => {
    state.selectedTemplate = e.target.value;
    updateTemplateBadges();
    loadDatabaseSchema();
  };
}

function renderTemplateOptions(templates) {
  const container = document.getElementById('template-cards-container');
  if (!container) return;
  container.innerHTML = '';

  if (templates.length === 0) {
    container.innerHTML = `
      <div class="col-span-3 p-5 text-center text-slate-500 panel-card rounded-lg text-xs">
        No active templates found in MySQL database. Please verify connection.
      </div>
    `;
    return;
  }

  templates.forEach(t => {
    const isSelected = t.template_name === state.selectedTemplate;
    const card = document.createElement('div');
    card.className = `p-4 rounded-xl cursor-pointer transition-all ${
      isSelected
        ? 'border-2 border-indigo-600 border-b-4 border-b-indigo-800 bg-indigo-50/50 shadow-md transform -translate-y-0.5'
        : 'card-3d hover:border-indigo-300'
    }`;
    card.onclick = () => selectTemplate(t.template_name);

    card.innerHTML = `
      <div class="flex items-start justify-between mb-2">
        <div>
          <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200 mb-1">
            ${t.output_file_name || t.template_name + '.dat'}
          </span>
          <h4 class="text-xs font-bold text-slate-900">${t.template_name}</h4>
        </div>
        <div class="w-4 h-4 rounded-full border ${isSelected ? 'bg-indigo-600 border-indigo-600' : 'border-slate-300'} flex items-center justify-center">
          ${isSelected ? '<svg class="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>' : ''}
        </div>
      </div>
      <p class="text-[11px] text-slate-500 mb-2.5 line-clamp-2">${t.description || 'Oracle Fusion HDL template object bundle.'}</p>
      <div class="flex flex-wrap gap-1">
        ${(t.objects || []).slice(0, 5).map(o => `
          <span class="text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200 font-medium">${o}</span>
        `).join('')}
        ${(t.objects || []).length > 5 ? `<span class="text-[10px] text-indigo-600 font-bold">+${t.objects.length - 5} more</span>` : ''}
      </div>
    `;
    container.appendChild(card);
  });
}

function updateTemplateBadges() {
  const current = state.templates.find(t => t.template_name === state.selectedTemplate);
  const badge = document.getElementById('current-template-badge');
  const targetMapTmpl = document.getElementById('map-target-template');
  const genTargetHeading = document.getElementById('gen-target-heading');
  const genTargetDatName = document.getElementById('gen-target-datname');

  const datName = current ? (current.output_file_name || `${state.selectedTemplate}.dat`) : `${state.selectedTemplate}.dat`;

  if (badge) {
    if (current) {
      badge.textContent = `${datName} (${current.objects_count} Objects)`;
    } else {
      badge.textContent = datName;
    }
  }

  if (targetMapTmpl) targetMapTmpl.textContent = state.selectedTemplate;
  if (genTargetHeading) genTargetHeading.textContent = `Ready to Generate ${datName}`;
  if (genTargetDatName) genTargetDatName.textContent = datName;
}

function selectTemplate(templateName) {
  state.selectedTemplate = templateName;
  renderTemplateOptions(state.templates);
  updateTemplateBadges();
  triggerAutoDetect();
}

// Load Input Excel Files
async function loadInputFiles() {
  try {
    const res = await fetch('/api/inputs');
    const files = await res.json();
    state.inputs = files;
    renderInputFileOptions(files);
    updateFileBadges();
    loadDataGrid();
  } catch (err) {
    showToast('Failed to load input files: ' + err.message, 'error');
  }
}

function renderInputFileOptions(files) {
  const container = document.getElementById('input-files-list');
  if (!container) return;
  container.innerHTML = '';

  if (files.length === 0) {
    container.innerHTML = `<div class="p-3 text-center text-xs text-slate-400">No Excel workbooks found in input/ directory.</div>`;
    return;
  }

  files.forEach(f => {
    const isSelected = f.path === state.selectedInput;
    const item = document.createElement('div');
    item.className = `flex items-center justify-between p-3 rounded-xl transition-all cursor-pointer ${
      isSelected
        ? 'bg-emerald-50/90 border-2 border-emerald-500 border-b-3 border-b-emerald-600 shadow-sm'
        : 'bg-white border border-slate-200 border-b-2 border-b-slate-300 hover:border-slate-300 hover:bg-slate-50'
    }`;
    item.onclick = () => selectInputFile(f.path);

    item.innerHTML = `
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center justify-center font-black text-[11px] shadow-2xs">
          XLS
        </div>
        <div>
          <div class="text-xs font-bold text-slate-900">${escapeHtml(f.filename)}</div>
          <div class="text-[10px] text-slate-500 font-medium">${f.size_kb} KB • Modified ${f.modified}</div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        ${isSelected ? '<span class="text-[10px] font-bold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full border border-emerald-300">Active Sheet</span>' : ''}
        <div class="w-4 h-4 rounded-full border ${isSelected ? 'bg-emerald-600 border-emerald-600' : 'border-slate-300'} flex items-center justify-center">
          ${isSelected ? '<svg class="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>' : ''}
        </div>
      </div>
    `;
    container.appendChild(item);
  });
}

function updateFileBadges() {
  const fileName = state.selectedInput.split(/[/\\]/).pop();
  const fileBadge = document.getElementById('current-file-badge');
  const targetMapFile = document.getElementById('map-target-file');
  if (fileBadge) fileBadge.textContent = fileName;
  if (targetMapFile) targetMapFile.textContent = fileName;
}

function selectInputFile(path) {
  state.selectedInput = path;
  renderInputFileOptions(state.inputs);
  updateFileBadges();
  state.dataGrid.page = 1;
  loadDataGrid();
  triggerAutoDetect();
}

// Drag & Drop File Upload
function setupFileUpload() {
  const dropzone = document.getElementById('file-dropzone');
  const fileInput = document.getElementById('excel-file-input');
  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', (e) => {
    if (e.target !== fileInput) {
      fileInput.click();
    }
  });

  ['dragenter', 'dragover'].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      dropzone.classList.add('border-emerald-500', 'bg-emerald-50/60');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      dropzone.classList.remove('border-emerald-500', 'bg-emerald-50/60');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadFile(files[0]);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) uploadFile(fileInput.files[0]);
  });
}

async function uploadFile(file) {
  if (!file.name.match(/\.(xlsx|xls)$/i)) {
    showToast('Please upload an Excel workbook (.xlsx or .xls)', 'warning');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    showToast(`Uploading ${file.name}...`, 'info');
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || 'Upload failed');

    showToast(`Successfully uploaded ${result.filename}`, 'success');
    await loadInputFiles();
    selectInputFile(result.path);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Auto-Detect Parameters
async function triggerAutoDetect() {
  if (!state.selectedInput) return;
  const btn = document.getElementById('btn-autodetect');
  if (btn) btn.innerHTML = 'Detecting...';

  try {
    const res = await fetch(`/api/defaults?file_path=${encodeURIComponent(state.selectedInput)}&template_name=${encodeURIComponent(state.selectedTemplate)}`);
    const data = await res.json();
    if (res.ok) {
      state.detectedDefaults = data;
      document.getElementById('input-legislation-code').value = data.legislation_code || '';
      document.getElementById('input-legal-employer').value = data.legal_employer_name || '';
      document.getElementById('input-source-owner').value = data.source_system_owner || 'GRISMO';

      document.getElementById('badge-detected-legislation').textContent = data.legislation_code || 'Auto';
      document.getElementById('badge-detected-employer').textContent = data.legal_employer_name || 'Auto';
      document.getElementById('badge-detected-owner').textContent = data.source_system_owner || 'Auto';
    }
  } catch (err) {
    console.warn('Auto-detect error:', err);
  } finally {
    if (btn) {
      btn.innerHTML = `
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
        <span>Auto-Detect Parameters</span>
      `;
    }
  }
}

// HDL Generation Pipeline Execution
async function executeGeneration() {
  if (state.isGenerating) return;
  state.isGenerating = true;

  const btn = document.getElementById('btn-execute-generate');
  btn.disabled = true;
  btn.innerHTML = 'Transforming & Generating HDL...';

  const progressSection = document.getElementById('generation-progress-box');
  const progressBar = document.getElementById('generation-progress-bar');
  const progressText = document.getElementById('generation-progress-text');

  progressSection.classList.remove('hidden');
  progressBar.style.width = '25%';
  progressText.textContent = 'Connecting to database and reading input Excel...';

  const payload = {
    file_path: state.selectedInput,
    template_name: state.selectedTemplate,
    legislation_code: document.getElementById('input-legislation-code').value.trim() || null,
    legal_employer_name: document.getElementById('input-legal-employer').value.trim() || null,
    source_system_owner: document.getElementById('input-source-owner').value.trim() || null,
  };

  try {
    progressBar.style.width = '65%';
    progressText.textContent = 'Mapping objects, validating national IDs, generating records...';

    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || 'Generation failed');

    progressBar.style.width = '100%';
    progressText.textContent = 'HDL bundle and audit reports generated successfully!';
    state.generationResult = result;

    renderGenerationResults(result);
    showToast(`HDL generation complete: ${result.generated_rows} records generated`, 'success');
    await loadOutputFiles();
  } catch (err) {
    progressBar.style.width = '100%';
    progressBar.classList.remove('from-indigo-600', 'to-blue-600');
    progressBar.classList.add('bg-rose-600');
    progressText.textContent = 'Error: ' + err.message;
    showToast(err.message, 'error');
  } finally {
    state.isGenerating = false;
    btn.disabled = false;
    btn.innerHTML = 'Execute Transformation & Generate HDL Bundle';
  }
}

function renderGenerationResults(res) {
  const container = document.getElementById('generation-results-card');
  if (!container) return;
  container.classList.remove('hidden');

  document.getElementById('res-stat-read').textContent = res.total_excel_rows;
  document.getElementById('res-stat-generated').textContent = res.generated_rows;
  document.getElementById('res-stat-skipped').textContent = res.skipped_rows;
  document.getElementById('res-stat-errors').textContent = res.validation_errors_count;
  document.getElementById('res-stat-filesize').textContent = res.output_file_size_kb + ' KB';

  // Quick download DAT button
  const quickDownload = document.getElementById('btn-quick-download-dat');
  if (quickDownload) {
    quickDownload.onclick = () => {
      window.location.href = `/api/reports/download/output/${res.output_filename}`;
    };
  }

  // Inline validation errors table
  const errorsCard = document.getElementById('validation-errors-inline-card');
  const errorsTbody = document.getElementById('validation-errors-table-body');
  if (res.validation_errors && res.validation_errors.length > 0) {
    errorsCard.classList.remove('hidden');
    errorsTbody.innerHTML = res.validation_errors.map(err => `
      <tr class="hover:bg-rose-50/50 transition-colors">
        <td class="py-1.5 px-3 font-mono text-slate-500 font-semibold">${err.ExcelRow || '—'}</td>
        <td class="py-1.5 px-3 font-bold text-slate-800">${err.Object || 'Worker'}</td>
        <td class="py-1.5 px-3 font-mono text-indigo-700 font-semibold">${err.Field || '—'}</td>
        <td class="py-1.5 px-3 text-rose-700 font-semibold">${escapeHtml(err.Error || '')}</td>
      </tr>
    `).join('');
  } else {
    errorsCard.classList.add('hidden');
  }
}

// Data Grid Spreadsheet View (Embedded on Upload Tab)
async function loadDataGrid() {
  const tableHead = document.getElementById('grid-table-head');
  const tableBody = document.getElementById('grid-table-body');
  if (!tableHead || !tableBody) return;

  tableBody.innerHTML = `<tr><td colspan="10" class="text-center py-6 text-slate-400 text-xs">Loading spreadsheet data...</td></tr>`;

  try {
    const query = `/api/excel/preview?file_path=${encodeURIComponent(state.selectedInput)}&page=${state.dataGrid.page}&page_size=${state.dataGrid.pageSize}&search=${encodeURIComponent(state.dataGrid.search)}`;
    const res = await fetch(query);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    state.dataGrid.totalRows = data.total_rows;
    state.dataGrid.totalPages = data.total_pages;
    state.dataGrid.columns = data.columns;
    state.dataGrid.rows = data.rows;

    document.getElementById('grid-total-rows-badge').textContent = `${data.total_rows} Rows`;
    document.getElementById('grid-total-cols-badge').textContent = `${data.columns.length} Columns`;
    document.getElementById('grid-filename-badge').textContent = data.filename;

    const startRow = (data.current_page - 1) * data.page_size + 1;
    const endRow = Math.min(data.current_page * data.page_size, data.filtered_rows);
    document.getElementById('grid-page-indicator').textContent =
      data.filtered_rows > 0 ? `Showing ${startRow}–${endRow} of ${data.filtered_rows} rows (Page ${data.current_page} of ${data.total_pages})` : '0 rows';

    // Render Headers
    tableHead.innerHTML = `
      <tr>
        <th class="py-2.5 px-3 text-left w-14"># Row</th>
        ${data.columns.map(col => `
          <th class="py-2.5 px-3 text-left whitespace-nowrap">${escapeHtml(col)}</th>
        `).join('')}
      </tr>
    `;

    // Render Rows
    if (data.rows.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="${data.columns.length + 1}" class="text-center py-6 text-slate-400 text-xs">No rows matched your search.</td></tr>`;
      return;
    }

    tableBody.innerHTML = data.rows.map(row => `
      <tr class="transition-colors hover:bg-slate-50">
        <td class="py-1.5 px-3 font-mono text-slate-400 bg-slate-50 font-medium">${row._row_number}</td>
        ${data.columns.map(col => `
          <td class="py-1.5 px-3 text-slate-700 whitespace-nowrap max-w-xs truncate" title="${escapeHtml(row[col] || '')}">
            ${escapeHtml(row[col] || '')}
          </td>
        `).join('')}
      </tr>
    `).join('');

  } catch (err) {
    tableBody.innerHTML = `<tr><td colspan="10" class="text-center py-6 text-rose-600 text-xs">Failed to load data: ${err.message}</td></tr>`;
  }
}

// Field Mappings Tab View
async function loadFieldMappings() {
  const tbody = document.getElementById('mappings-table-body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-400 text-xs">Analyzing field mappings...</td></tr>`;

  try {
    const res = await fetch(`/api/mappings/preview?file_path=${encodeURIComponent(state.selectedInput)}&template_name=${encodeURIComponent(state.selectedTemplate)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    state.mappings.data = data.mappings;

    document.getElementById('map-stat-total').textContent = data.total_fields;
    document.getElementById('map-stat-mapped').textContent = data.mapped_count;
    document.getElementById('map-stat-unmapped').textContent = data.unmapped_count;

    renderFilteredMappings();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-rose-600 text-xs">Failed to load mappings: ${err.message}</td></tr>`;
  }
}

function renderFilteredMappings() {
  const tbody = document.getElementById('mappings-table-body');
  if (!tbody) return;

  const filter = state.mappings.filter;
  const search = state.mappings.search.toLowerCase();

  const filtered = state.mappings.data.filter(m => {
    if (filter === 'mapped' && m.status !== 'MAPPED') return false;
    if (filter === 'unmapped' && m.status !== 'UNMAPPED') return false;
    if (filter === 'direct' && m.mapping_type !== 'DIRECT') return false;
    if (filter === 'generated' && m.mapping_type !== 'GENERATED') return false;
    if (filter === 'default' && m.mapping_type !== 'DEFAULT') return false;

    if (search) {
      const matchField = (m.field_name || '').toLowerCase().includes(search);
      const matchObj = (m.object_name || '').toLowerCase().includes(search);
      const matchCol = (m.excel_column || '').toLowerCase().includes(search);
      return matchField || matchObj || matchCol;
    }
    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-slate-400 text-xs">No mappings matched your filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(m => {
    const isMapped = m.status === 'MAPPED';
    const typeBadgeClass =
      m.mapping_type === 'DIRECT' ? 'bg-blue-100 text-blue-800 border-blue-200' :
      m.mapping_type === 'GENERATED' ? 'bg-indigo-100 text-indigo-800 border-indigo-200' :
      m.mapping_type === 'DEFAULT' ? 'bg-purple-100 text-purple-800 border-purple-200' :
      'bg-slate-100 text-slate-600 border-slate-200';

    return `
      <tr class="hover:bg-slate-50 transition-colors">
        <td class="py-2 px-3 font-mono text-slate-600 font-medium">${escapeHtml(m.object_name)}</td>
        <td class="py-2 px-3 font-bold text-slate-900">${escapeHtml(m.field_name)}</td>
        <td class="py-2 px-3 text-slate-700">
          ${m.excel_column ? `<span class="bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-mono text-emerald-900 font-semibold">${escapeHtml(m.excel_column)}</span>` : '<span class="text-slate-400">—</span>'}
        </td>
        <td class="py-2 px-3">
          ${m.mapping_type ? `<span class="px-2 py-0.5 rounded border text-[10px] font-bold ${typeBadgeClass}">${m.mapping_type}</span>` : '<span class="text-slate-400">—</span>'}
        </td>
        <td class="py-2 px-3 text-slate-600 font-mono text-[11px]">
          ${m.default_value ? escapeHtml(m.default_value) : '<span class="text-slate-400">—</span>'}
        </td>
        <td class="py-2 px-3">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-black tracking-wide ${
            isMapped ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' : 'bg-rose-100 text-rose-800 border border-rose-300'
          }">
            ${isMapped ? 'MAPPED' : 'UNMAPPED'}
          </span>
        </td>
      </tr>
    `;
  }).join('');
}

// ================= OUTPUTS TAB: FULL DATA VISIBLE, DOWNLOAD & COPY =================
async function loadOutputFiles() {
  const selectorContainer = document.getElementById('outputs-file-selector');
  if (!selectorContainer) return;

  try {
    const res = await fetch('/api/reports');
    const data = await res.json();
    state.outputs.files = data.outputs;
    state.outputs.reports = data.reports;

    renderOutputsFileSelector();
  } catch (err) {
    showToast('Failed to load output files: ' + err.message, 'error');
  }
}

function renderOutputsFileSelector() {
  const container = document.getElementById('outputs-file-selector');
  if (!container) return;
  container.innerHTML = '';

  const allItems = [
    ...state.outputs.files.map(item => ({ ...item, category: 'output', isDat: true })),
    ...state.outputs.reports.map(item => ({ ...item, category: 'reports', isDat: false }))
  ];

  if (allItems.length === 0) {
    container.innerHTML = `<div class="p-2 text-xs text-slate-400">No generated files yet. Generate in HDL Generator.</div>`;
    document.getElementById('output-data-viewer').innerHTML = `
      <div class="py-8 text-center text-slate-400 text-xs">
        No output data available to display. Generate an HDL file in the HDL Generator tab.
      </div>
    `;
    return;
  }

  // If active file is not selected, select the first one
  if (!state.outputs.activeFile || !allItems.some(i => i.filename === state.outputs.activeFile)) {
    state.outputs.activeFile = allItems[0].filename;
    state.outputs.activeCategory = allItems[0].category;
  }

  allItems.forEach(item => {
    const isSelected = item.filename === state.outputs.activeFile;
    const btn = document.createElement('button');
    const isDat = item.isDat;
    const isXlsx = item.filename.endsWith('.xlsx');
    const isCsv = item.filename.endsWith('.csv');

    const typeBadge = isDat ? 'DAT' : isXlsx ? 'XLSX' : 'CSV';
    const tagBg = isDat ? 'bg-indigo-950 text-indigo-400 border border-indigo-800' :
                  isXlsx ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                  'bg-rose-950 text-rose-400 border border-rose-800';

    btn.className = `dark-tab-btn ${isSelected ? 'active' : ''}`;
    btn.onclick = () => selectOutputFile(item.filename, item.category);

    btn.innerHTML = `
      <span class="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded font-black ${tagBg}">${typeBadge}</span>
      <span class="font-mono text-xs">${escapeHtml(item.filename)}</span>
      <span class="text-[10px] text-slate-500 font-normal">${item.size_kb} KB</span>
    `;
    container.appendChild(btn);
  });

  // Display the active file content
  displayActiveOutputContent();
}

function selectOutputFile(filename, category) {
  state.outputs.activeFile = filename;
  state.outputs.activeCategory = category;
  renderOutputsFileSelector();
}

async function displayActiveOutputContent() {
  const viewer = document.getElementById('output-data-viewer');
  const title = document.getElementById('active-file-title');
  const subtitle = document.getElementById('active-file-subtitle');
  const badge = document.getElementById('active-file-badge');
  const downloadBtn = document.getElementById('btn-download-active-file');

  const filename = state.outputs.activeFile;
  const category = state.outputs.activeCategory;
  if (!filename || !viewer) return;

  const isDat = filename.endsWith('.dat');
  const isXlsx = filename.endsWith('.xlsx');
  const isCsv = filename.endsWith('.csv');

  title.textContent = filename;
  badge.textContent = isDat ? 'DAT' : isXlsx ? 'XLSX' : 'CSV';
  badge.className = isDat ? 'px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 font-bold font-mono text-[10px] border border-indigo-800' :
                    isXlsx ? 'px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 font-bold font-mono text-[10px] border border-emerald-800' :
                    'px-2 py-0.5 rounded bg-rose-950 text-rose-400 font-bold font-mono text-[10px] border border-rose-800';

  downloadBtn.href = `/api/reports/download/${category}/${filename}`;

  viewer.innerHTML = `<div class="py-12 text-center text-slate-500 text-xs font-mono">Loading deliverable records...</div>`;

  try {
    if (isDat) {
      // DAT file preview with DARK THEME and NORMAL compact line spacing
      const res = await fetch(`/api/reports/preview-dat/${encodeURIComponent(filename)}?max_lines=1500`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);

      subtitle.textContent = `${data.metadata_lines} METADATA lines • ${data.merge_lines} MERGE lines • Total ${data.lines.length} lines`;
      state.outputs.activeRawText = data.lines.join('\n');

      viewer.innerHTML = `
        <div class="dat-viewer-dark">
          ${data.lines.map((line, idx) => {
            const isMeta = line.startsWith('METADATA|');
            return `
              <div class="dat-row">
                <span class="dat-linenum">${idx + 1}</span>
                <span class="dat-content ${isMeta ? 'dat-content-metadata' : 'dat-content-merge'}">${escapeHtml(line)}</span>
              </div>
            `;
          }).join('')}
        </div>
      `;

    } else if (isCsv) {
      // CSV report preview with DARK THEME table (e.g. validation_errors.csv)
      const res = await fetch(`/api/reports/preview-csv/${encodeURIComponent(filename)}?max_rows=500`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);

      subtitle.textContent = `${data.total_rows} total records in audit report`;

      // Build TSV for copying to Excel/text
      const headerRow = data.columns.join('\t');
      const rowsText = data.rows.map(r => data.columns.map(c => r[c] ?? '').join('\t')).join('\n');
      state.outputs.activeRawText = headerRow + '\n' + rowsText;

      if (data.rows.length === 0) {
        viewer.innerHTML = `<div class="py-12 text-center text-xs text-slate-500 font-medium">File is empty (0 validation errors reported).</div>`;
        return;
      }

      viewer.innerHTML = `
        <div class="dark-table-container">
          <table class="dark-table">
            <thead>
              <tr>
                ${data.columns.map(c => `<th>${escapeHtml(c)}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${data.rows.map(r => `
                <tr>
                  ${data.columns.map(c => `
                    <td class="${c === 'Error' ? 'text-rose-400 font-bold' : ''}">
                      ${escapeHtml(r[c] ?? '')}
                    </td>
                  `).join('')}
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;

    } else if (isXlsx) {
      // Excel mapping report preview with DARK THEME table
      const res = await fetch(`/api/reports/preview-excel/${encodeURIComponent(filename)}?max_rows=500`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);

      subtitle.textContent = `${data.total_rows} total attribute mapping definitions`;

      // Build TSV for copying
      const headerRow = data.columns.join('\t');
      const rowsText = data.rows.map(r => data.columns.map(c => r[c] ?? '').join('\t')).join('\n');
      state.outputs.activeRawText = headerRow + '\n' + rowsText;

      viewer.innerHTML = `
        <div class="dark-table-container">
          <table class="dark-table">
            <thead>
              <tr>
                ${data.columns.map(c => `<th>${escapeHtml(c)}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${data.rows.map(r => `
                <tr>
                  ${data.columns.map(c => `
                    <td class="${c === 'status' && r[c] === 'MAPPED' ? 'text-emerald-400 font-bold' : ''}">
                      ${escapeHtml(r[c] ?? '')}
                    </td>
                  `).join('')}
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }
  } catch (err) {
    viewer.innerHTML = `<div class="py-12 text-center text-xs text-rose-400">Error reading file content: ${err.message}</div>`;
  }
}

function copyActiveFileOutput() {
  if (!state.outputs.activeRawText) {
    showToast('No content available to copy.', 'warning');
    return;
  }

  navigator.clipboard.writeText(state.outputs.activeRawText).then(() => {
    const copyBtnText = document.getElementById('btn-copy-text');
    if (copyBtnText) {
      const originalText = copyBtnText.textContent;
      copyBtnText.textContent = 'Copied to Clipboard!';
      setTimeout(() => {
        copyBtnText.textContent = originalText;
      }, 2000);
    }
    showToast(`Copied ${state.outputs.activeFile} contents to clipboard`, 'success');
  }).catch(err => {
    showToast('Failed to copy: ' + err.message, 'error');
  });
}

// Database Schema Viewer
async function loadDatabaseSchema() {
  const container = document.getElementById('db-schema-container');
  if (!container) return;

  container.innerHTML = `<div class="text-center py-6 text-slate-400 text-xs">Loading database structure...</div>`;

  try {
    const res = await fetch(`/api/templates/${encodeURIComponent(state.selectedTemplate)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    if (data.error || !data.objects || data.objects.length === 0) {
      container.innerHTML = `
        <div class="p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-950 space-y-1 text-xs">
          <div class="font-bold">Template Notice: ${data.template_name}</div>
          <p class="text-amber-800">${data.error || 'No active objects or attributes configured for this template in MySQL.'}</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="p-4 rounded-xl bg-gradient-to-r from-teal-50/60 via-cyan-50/40 to-slate-50 border border-teal-200 flex flex-wrap items-center justify-between gap-2.5 shadow-2xs">
        <div>
          <h3 class="text-xs font-bold text-slate-900">${data.template_name} Template Configuration</h3>
          <p class="text-[11px] text-slate-600">Output: <code class="font-mono text-teal-800 font-bold">${data.output_file_name}</code> • Source Owner: <code class="font-mono text-emerald-800 font-bold">${data.source_system_owner}</code></p>
        </div>
        <span class="px-2.5 py-1 rounded-md bg-teal-100 text-teal-800 border border-teal-300 text-xs font-bold">
          ${data.objects.length} Objects
        </span>
      </div>

      <div class="space-y-3 pt-1">
        ${data.objects.map(obj => `
          <div class="card-3d overflow-hidden">
            <div class="p-3 bg-slate-50/90 border-b border-slate-200 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-teal-600"></span>
                <span class="font-black text-xs text-slate-900">${obj.object_name}</span>
                <span class="text-[10px] text-slate-500 font-medium">(${obj.attribute_count} attributes)</span>
              </div>
              <span class="text-[11px] text-teal-800 font-bold bg-teal-50 px-2 py-0.5 rounded border border-teal-200">${obj.mappings_count} mapped</span>
            </div>
            <div class="p-3.5 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 bg-white">
              ${obj.attributes.map(attr => `
                <div class="p-2 rounded-lg ${attr.required ? 'border border-amber-300 border-b-2 border-b-amber-400 bg-amber-50/70 text-amber-950' : 'border border-slate-200 border-b-2 border-b-slate-300 bg-slate-50/80 text-slate-800'} text-xs">
                  <div class="font-bold truncate" title="${attr.field_name}">
                    ${attr.field_name}
                  </div>
                  <div class="text-[10px] ${attr.required ? 'text-amber-800' : 'text-slate-500'} flex justify-between mt-1 font-mono font-medium">
                    <span>${attr.data_type}</span>
                    ${attr.required ? '<span class="font-black bg-amber-200/80 px-1 rounded text-[9px]">REQ</span>' : ''}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="p-4 text-center text-xs text-rose-600">Error loading schema: ${err.message}</div>`;
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // Execute Generate Button
  document.getElementById('btn-execute-generate')?.addEventListener('click', executeGeneration);

  // Auto-detect button
  document.getElementById('btn-autodetect')?.addEventListener('click', triggerAutoDetect);

  // Copy active output button
  document.getElementById('btn-copy-active-file')?.addEventListener('click', copyActiveFileOutput);

  // Test DB connection button
  document.getElementById('btn-test-db')?.addEventListener('click', async () => {
    showToast('Testing MySQL connection...', 'info');
    const result = await refreshSystemStatus();
    if (result && result.database && result.database.status === 'connected') {
      showToast(`Connected to ${result.database.database} (MySQL ${result.database.version})`, 'success');
    } else {
      showToast('Database connection failed: ' + (result?.database?.error || 'Unknown error'), 'error');
    }
  });

  // Spreadsheet Data Grid Controls
  document.getElementById('grid-search-input')?.addEventListener('input', (e) => {
    state.dataGrid.search = e.target.value;
    state.dataGrid.page = 1;
    loadDataGrid();
  });

  document.getElementById('grid-pagesize-select')?.addEventListener('change', (e) => {
    state.dataGrid.pageSize = parseInt(e.target.value, 10);
    state.dataGrid.page = 1;
    loadDataGrid();
  });

  document.getElementById('grid-first-btn')?.addEventListener('click', () => {
    if (state.dataGrid.page > 1) {
      state.dataGrid.page = 1;
      loadDataGrid();
    }
  });

  document.getElementById('grid-prev-btn')?.addEventListener('click', () => {
    if (state.dataGrid.page > 1) {
      state.dataGrid.page--;
      loadDataGrid();
    }
  });

  document.getElementById('grid-next-btn')?.addEventListener('click', () => {
    if (state.dataGrid.page < state.dataGrid.totalPages) {
      state.dataGrid.page++;
      loadDataGrid();
    }
  });

  document.getElementById('grid-last-btn')?.addEventListener('click', () => {
    if (state.dataGrid.page < state.dataGrid.totalPages) {
      state.dataGrid.page = state.dataGrid.totalPages;
      loadDataGrid();
    }
  });

  // Mappings Filters
  document.querySelectorAll('.mapping-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.mapping-filter-btn').forEach(b => {
        b.className = 'mapping-filter-btn px-3 py-1 rounded-md text-xs font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors';
      });
      btn.className = 'mapping-filter-btn px-3 py-1 rounded-md text-xs font-bold bg-indigo-600 text-white transition-colors';
      state.mappings.filter = btn.getAttribute('data-filter');
      renderFilteredMappings();
    });
  });

  document.getElementById('mappings-search-input')?.addEventListener('input', (e) => {
    state.mappings.search = e.target.value;
    renderFilteredMappings();
  });
}

// Utility: escape HTML
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
