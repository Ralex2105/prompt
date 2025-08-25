const MAX_FILES = 50;
const WARNING_THRESHOLD = 4.0;
const DANGER_THRESHOLD = 5.0;
const MAX_POINTS_PER_FILE = 2000;

let fileStore = [];
let summaries = [];
let currentGraphRow = null; // Track the currently open graph row
let pollingInterval = null;
let previousSummaryCount = 0;

const elements = {
  fileInput: document.getElementById('fileInput'),
  selectFilesBtn: document.getElementById('selectFilesBtn'),
  startBtn: document.getElementById('startBtn'),
  summaryTbody: document.querySelector('#summaryTable tbody'),
  statusDiv: document.getElementById('statusDiv'),
  spinner: document.getElementById('spinner'),
  progressText: document.getElementById('progressText'),
  diagnostics: document.getElementById('diagnostics'),
  sampleInterval: document.getElementById('sampleInterval'),
  fromDate: document.getElementById('fromDate'),
  toDate: document.getElementById('toDate'),
  apiConnectBtn: document.getElementById('apiConnectBtn'),
  refreshFilesBtn: document.getElementById('refreshFilesBtn'),  // Added for the refresh button
  processingMessage: document.getElementById('processingMessage')
};

function init() {
  setupEventListeners();
  getSummaryResults(false);
  getUploadedFiles();
  previousSummaryCount = summaries.length;
}

function setupEventListeners() {
  elements.selectFilesBtn.addEventListener('click', () => elements.fileInput.click());
  elements.fileInput.addEventListener('change', handleFileSelect);
  if (elements.startBtn) { elements.startBtn.addEventListener('click', startAnalysis); }
  elements.apiConnectBtn.addEventListener('click', connectAPI);
  elements.refreshFilesBtn.addEventListener('click', () => {  // Added event listener for refresh files
    getUploadedFiles();
    getSummaryResults(false);
    showAlert('Список файлов и сводок обновлён', 'success');
    elements.processingMessage.style.display = 'none';
    elements.processingMessage.textContent = '';
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  });
}

async function handleFileSelect(e) {
  const files = Array.from(e.target.files).slice(0, MAX_FILES - fileStore.length);
  let addedCount = 0;
  for (const file of files) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData
      });
      if (response.ok) {
        fileStore.push({
          file,
          name: file.name,
          parsed: false,
          error: null,
          sampleData: [],
          stats: initStats()
        });
        addedCount++;
      } else {
        console.error('Upload failed:', response.statusText);
        showAlert(`Ошибка загрузки файла ${file.name}: ${response.statusText}`, 'error');
      }
    } catch (error) {
      console.error('Upload error:', error);
      showAlert(`Ошибка загрузки файла ${file.name}: ${error.message}`, 'error');
    }
  }
  if (addedCount > 0) {
    showAlert(`Добавлено ${addedCount} файлов`, 'success');
    elements.processingMessage.textContent = 'Файл обрабатывается...';
    elements.processingMessage.style.display = 'block';
    startPolling();
  }
  e.target.value = '';
}

function startPolling() {
  if (pollingInterval) clearInterval(pollingInterval);
  previousSummaryCount = summaries.length;
  pollingInterval = setInterval(async () => {
    try {
      const response = await fetch('/get_summary');
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      if (data.summaries && data.summaries.length > previousSummaryCount) {
        elements.processingMessage.textContent = 'Новый файл в summary готов. Нажмите "Обновить" для просмотра.';
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
    } catch (error) {
      console.error('Polling error:', error);
    }
  }, 5000); // Poll every 5 seconds
}

async function getSummaryResults(withDelay = false) {
  try {
    showSpinner('Загрузка результатов анализа...');
    if (withDelay) {
      await new Promise(resolve => setTimeout(resolve, 15000));
    }
    const response = await fetch('/get_summary');
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    console.log('getSummaryResults response:', data);
    hideSpinner();
    summaries = data.summaries || [];
    updateSummaryTable();
    showAlert('Результаты анализа загружены', 'success');
  } catch (error) {
    console.error('getSummaryResults error:', error);
    hideSpinner();
    showAlert(`Ошибка: ${error.message}`, 'error');
  }
}

function updateSummaryTable() {
  elements.summaryTbody.innerHTML = '';
  summaries.forEach(summary => {
    const tr = document.createElement('tr');
    tr.dataset.filename = summary.filename;
    tr.innerHTML = `
      <td>${summary.filename}</td>
      <td>${summary.analysis_time || 'N/A'}</td>
      <td>${summary.summary_defect || 'N/A'}</td>
      <td>${summary.summary_severity || 'N/A'}</td>
      <td>
        <button class="btn small danger" onclick="deleteSummaryFile('${summary.filename}')">🗑️ Удалить</button>
        <button class="btn small" onclick="showCharts('${summary.filename}', this.parentElement.parentElement)">📊 График</button>
        <button class="btn small" onclick="downloadSummaryFile('${summary.filename}')">📥 Загрузить</button>
      </td>
    `;
    elements.summaryTbody.appendChild(tr);
  });
}

async function deleteSummaryFile(filename) {
  try {
    showSpinner('Удаление файла...');
    const response = await fetch(`/delete_file/${filename}`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    hideSpinner();
    showAlert(data.message, 'success');
    if (currentGraphRow && currentGraphRow.dataset.filename === filename) {
      currentGraphRow.remove();
      currentGraphRow = null;
    }
    await getSummaryResults(false);
    await getUploadedFiles();
  } catch (error) {
    console.error('deleteSummaryFile error:', error);
    hideSpinner();
    showAlert(`Ошибка при удалении файла: ${error.message}`, 'error');
  }
}

async function showCharts(filename, row) {
  try {
    // Check if the graph for this row is already open
    if (currentGraphRow && currentGraphRow.dataset.filename === filename) {
      // Close the current graph
      currentGraphRow.remove();
      currentGraphRow = null;
      return;
    }

    // Close any other open graph
    if (currentGraphRow) {
      currentGraphRow.remove();
      currentGraphRow = null;
    }

    showSpinner('Загрузка данных для графиков...');
    const response = await fetch(`/download_summary/${filename}`);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const csvText = await response.text();
    const parsed = Papa.parse(csvText, {
      header: true,
      skipEmptyLines: true,
      transform: (value) => value.trim()
    });
    const data = parsed.data;
    if (!data || data.length === 0) {
      throw new Error('Нет данных для построения графиков');
    }
    hideSpinner();

    // Create a new row for graphs (inserted after the current row to appear below)
    const graphTr = document.createElement('tr');
    graphTr.dataset.filename = filename;
    const td = document.createElement('td');
    td.colSpan = 5;

    const container = document.createElement('div');
    container.className = 'chart-container';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '20px';

    const chart1 = document.createElement('div');
    chart1.id = `chart1_${filename}`;
    chart1.style.width = '100%';
    chart1.style.height = '450px';

    const chart2 = document.createElement('div');
    chart2.id = `chart2_${filename}`;
    chart2.style.width = '100%';
    chart2.style.height = '450px';

    const chart3 = document.createElement('div');
    chart3.id = `chart3_${filename}`;
    chart3.style.width = '100%';
    chart3.style.height = '450px';

    container.appendChild(chart1);
    container.appendChild(chart2);
    container.appendChild(chart3);
    td.appendChild(container);
    graphTr.appendChild(td);

    // Insert the graph row after the current row (to appear below)
    row.parentNode.insertBefore(graphTr, row.nextSibling);

    // Plot the charts
    const trace1 = {
      x: data.map(row => parseFloat(row['f1'])),
      y: data.map(row => parseFloat(row['f2'])),
      mode: 'lines+markers',
      name: 'f1 vs f2',
      type: 'scatter'
    };
    Plotly.newPlot(chart1.id, [trace1], {
      title: 'График f1 vs f2',
      xaxis: { title: 'f1' },
      yaxis: { title: 'f2' },
      margin: { t: 50 }
    });

    const trace2 = {
      x: data.map(row => parseFloat(row['f3'])),
      y: data.map(row => parseFloat(row['f4'])),
      mode: 'lines+markers',
      name: 'f3 vs f4',
      type: 'scatter'
    };
    Plotly.newPlot(chart2.id, [trace2], {
      title: 'График f3 vs f4',
      xaxis: { title: 'f3' },
      yaxis: { title: 'f4' },
      margin: { t: 50 }
    });

    const trace3 = [
      { x: data.map(row => parseFloat(row['f5'])), y: data.map((_, i) => i), mode: 'lines', name: 'f5' },
      { x: data.map(row => parseFloat(row['f6'])), y: data.map((_, i) => i), mode: 'lines', name: 'f6' },
      { x: data.map(row => parseFloat(row['f7'])), y: data.map((_, i) => i), mode: 'lines', name: 'f7' },
      { x: data.map(row => parseFloat(row['f8'])), y: data.map((_, i) => i), mode: 'lines', name: 'f8' },
      { x: data.map(row => parseFloat(row['f9'])), y: data.map((_, i) => i), mode: 'lines', name: 'f9' }
    ];
    Plotly.newPlot(chart3.id, trace3, {
      title: 'График f5-f9',
      xaxis: { title: 'Значения' },
      yaxis: { title: 'Индекс' },
      margin: { t: 50 }
    });

    currentGraphRow = graphTr;
    showAlert('Графики построены', 'success');
  } catch (error) {
    console.error('showCharts error:', error);
    hideSpinner();
    showAlert(`Ошибка при построении графиков: ${error.message}`, 'error');
  }
}

async function downloadSummaryFile(filename) {
  try {
    showSpinner('Скачивание файла...');
    const response = await fetch(`/download_summary/${filename}`);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    hideSpinner();
    showAlert(`Файл ${filename} успешно скачан`, 'success');
  } catch (error) {
    console.error('downloadSummaryFile error:', error);
    hideSpinner();
    showAlert(`Ошибка при скачивании: ${error.message}`, 'error');
  }
}

async function getUploadedFiles() {
  try {
    showSpinner('Загрузка списка файлов...');
    const response = await fetch('/get_uploaded_files');
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    console.log('getUploadedFiles response:', data);
    hideSpinner();
    if (data.files && data.files.length > 0) {
      fileStore = data.files.map(filename => ({
        file: null,
        name: filename,
        parsed: false,
        error: null,
        sampleData: [],
        stats: initStats()
      }));
      showAlert(`Загружено ${data.files.length} файлов с сервера`, 'success');
    } else {
      fileStore = [];
      showAlert('Нет загруженных файлов', 'warning');
    }
  } catch (error) {
    console.error('getUploadedFiles error:', error);
    hideSpinner();
    showAlert(`Ошибка при загрузке списка файлов: ${error.message}`, 'error');
  }
}

function initStats() { return { mean: 0, min: 0, max: 0, std: 0, phase: '' }; }
function startAnalysis() { /* Placeholder */ }
function connectAPI() { /* Placeholder */ }
function showSpinner(text) { elements.spinner.classList.remove('hidden'); elements.progressText.textContent = text || 'Обработка...'; }
function hideSpinner() { elements.spinner.classList.add('hidden'); elements.progressText.textContent = ''; }
function showAlert(message, type) {
  const alert = document.createElement('div');
  alert.className = `diagnostic-item ${type}`;
  alert.textContent = message;
  elements.diagnostics.prepend(alert);
  setTimeout(() => {
    alert.remove();
  }, 5000);
}

init();