const MAX_FILES = 50;
const WARNING_THRESHOLD = 4.0;
const DANGER_THRESHOLD = 5.0;
const MAX_POINTS_PER_FILE = 2000;

let fileStore = [];
let allStats = [];
let traces = [];
let anomalyDetected = false;
let startTime = Date.now();
let summaries = [];

const elements = {
  fileInput: document.getElementById('fileInput'),
  selectFilesBtn: document.getElementById('selectFilesBtn'),
  startBtn: document.getElementById('startBtn'),
  statsTbody: document.querySelector('#statsTable tbody'),
  summaryTbody: document.querySelector('#summaryTable tbody'),
  statusDiv: document.getElementById('statusDiv'),
  chart1: document.getElementById('chart1'),
  chart2: document.getElementById('chart2'),
  chart3: document.getElementById('chart3'),
  spinner: document.getElementById('spinner'),
  progressText: document.getElementById('progressText'),
  diagnostics: document.getElementById('diagnostics'),
  llmOutput: document.getElementById('llmOutput'),
  llmText: document.getElementById('llmText'),
  llmTitle: document.getElementById('llmTitle'),
  analyzeBtn: document.getElementById('analyzeBtn'),
  downloadStatsBtn: document.getElementById('downloadStatsBtn'),
  copyReportBtn: document.getElementById('copyReportBtn'),
  saveReportBtn: document.getElementById('saveReportBtn'),
  sendReportBtn: document.getElementById('sendReportBtn'),
  sampleInterval: document.getElementById('sampleInterval'),
  fromDate: document.getElementById('fromDate'),
  toDate: document.getElementById('toDate'),
  applyTimeRangeBtn: document.getElementById('applyTimeRangeBtn'),
  apiConnectBtn: document.getElementById('apiConnectBtn'),
  refreshSummaryBtn: document.getElementById('refreshSummaryBtn')
};

function init() {
  setupEventListeners();
  getSummaryResults(false);
  getUploadedFiles();
}

function setupEventListeners() {
  elements.selectFilesBtn.addEventListener('click', () => elements.fileInput.click());
  elements.fileInput.addEventListener('change', handleFileSelect);
  if (elements.startBtn) { elements.startBtn.addEventListener('click', startAnalysis); }
  elements.analyzeBtn.addEventListener('click', () => getSummaryResults(true));
  elements.downloadStatsBtn.addEventListener('click', downloadStats);
  elements.copyReportBtn.addEventListener('click', copyReport);
  elements.saveReportBtn.addEventListener('click', saveReport);
  elements.sendReportBtn.addEventListener('click', sendReport);
  elements.applyTimeRangeBtn.addEventListener('click', drawChart);
  elements.apiConnectBtn.addEventListener('click', connectAPI);
  elements.refreshSummaryBtn.addEventListener('click', () => getSummaryResults(false));
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
    updateFileList();
    showAlert(`Добавлено ${addedCount} файлов`, 'success');
  }
  e.target.value = '';
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
    if (summaries.length > 0) {
      let text = `Результаты анализа (${new Date().toLocaleString()})\n\n`;
      summaries.forEach(summary => {
        text += `Файл: ${summary.filename}\n`;
        text += `Основной дефект: ${summary.summary_defect || 'N/A'}\n`;
        text += `Серьезность: ${summary.summary_severity || 'N/A'}\n`;
        text += `Дополнительно: ${summary.additional_note || 'N/A'}\n`;
        text += `Время анализа: ${summary.analysis_time || 'N/A'}\n`;
        text += `------------------------\n`;
      });
      showAnalysisResult(text);
      elements.llmTitle.textContent = 'Результаты анализа';
      showAlert('Результаты анализа загружены', 'success');
    } else {
      showAnalysisResult(data.message || 'Нет доступных результатов анализа.');
      showAlert(data.message || 'Нет данных для отображения', 'warning');
    }
  } catch (error) {
    console.error('getSummaryResults error:', error);
    hideSpinner();
    showAnalysisResult('Ошибка при загрузке результатов анализа.');
    showAlert(`Ошибка: ${error.message}`, 'error');
  }
}

function updateSummaryTable() {
  elements.summaryTbody.innerHTML = '';
  summaries.forEach(summary => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${summary.filename}</td>
      <td>${summary.analysis_time || 'N/A'}</td>
      <td>${summary.summary_defect || 'N/A'}</td>
      <td>${summary.summary_severity || 'N/A'}</td>
      <td>
        <button class="btn small danger" onclick="deleteSummaryFile('${summary.filename}')">🗑️ Удалить</button>
        <button class="btn small" onclick="showCharts('${summary.filename}')">📊 График</button>
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
    await getSummaryResults(false);
    await getUploadedFiles();
  } catch (error) {
    console.error('deleteSummaryFile error:', error);
    hideSpinner();
    showAlert(`Ошибка при удалении файла: ${error.message}`, 'error');
  }
}

async function showCharts(filename) {
  try {
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

    // Chart 1: f1 vs f2
    const trace1 = {
      x: data.map(row => parseFloat(row['f1'])),
      y: data.map(row => parseFloat(row['f2'])),
      mode: 'lines+markers',
      name: 'f1 vs f2',
      type: 'scatter'
    };
    Plotly.newPlot(elements.chart1, [trace1], {
      title: 'График f1 vs f2',
      xaxis: { title: 'f1' },
      yaxis: { title: 'f2' },
      margin: { t: 50 }
    });

    // Chart 2: f3 vs f4
    const trace2 = {
      x: data.map(row => parseFloat(row['f3'])),
      y: data.map(row => parseFloat(row['f4'])),
      mode: 'lines+markers',
      name: 'f3 vs f4',
      type: 'scatter'
    };
    Plotly.newPlot(elements.chart2, [trace2], {
      title: 'График f3 vs f4',
      xaxis: { title: 'f3' },
      yaxis: { title: 'f4' },
      margin: { t: 50 }
    });

    // Chart 3: f5-f9
    const trace3 = [
      { x: data.map(row => parseFloat(row['f5'])), y: data.map((_, i) => i), mode: 'lines', name: 'f5' },
      { x: data.map(row => parseFloat(row['f6'])), y: data.map((_, i) => i), mode: 'lines', name: 'f6' },
      { x: data.map(row => parseFloat(row['f7'])), y: data.map((_, i) => i), mode: 'lines', name: 'f7' },
      { x: data.map(row => parseFloat(row['f8'])), y: data.map((_, i) => i), mode: 'lines', name: 'f8' },
      { x: data.map(row => parseFloat(row['f9'])), y: data.map((_, i) => i), mode: 'lines', name: 'f9' }
    ];
    Plotly.newPlot(elements.chart3, trace3, {
      title: 'График f5-f9',
      xaxis: { title: 'Значения' },
      yaxis: { title: 'Индекс' },
      margin: { t: 50 }
    });

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
      updateFileList();
      showAlert(`Загружено ${data.files.length} файлов с сервера`, 'success');
    } else {
      fileStore = [];
      updateFileList();
      showAlert('Нет загруженных файлов', 'warning');
    }
  } catch (error) {
    console.error('getUploadedFiles error:', error);
    hideSpinner();
    showAlert(`Ошибка при загрузке списка файлов: ${error.message}`, 'error');
  }
}

async function downloadStats() {
  try {
    showSpinner('Скачивание файла summary...');
    const response = await fetch('/get_summary');
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    console.log('downloadStats response:', data);
    hideSpinner();
    if (data.summaries && data.summaries.length > 0) {
      const latestSummary = data.summaries.sort((a, b) =>
        new Date(b.analysis_time || 0) - new Date(a.analysis_time || 0)
      )[0];
      const filename = latestSummary.filename;
      const downloadResponse = await fetch(`/download_summary/${filename}`);
      if (!downloadResponse.ok) {
        throw new Error(`HTTP error! Status: ${downloadResponse.status}`);
      }
      const blob = await downloadResponse.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showAlert(`Файл ${filename} успешно скачан`, 'success');
    } else {
      showAlert(data.message || 'Нет данных для скачивания', 'warning');
    }
  } catch (error) {
    console.error('downloadStats error:', error);
    hideSpinner();
    showAlert(`Ошибка при скачивании: ${error.message}`, 'error');
  }
}

function updateFileList() {
  // No file list dropdown, so this function is empty
}

function initStats() { return { mean: 0, min: 0, max: 0, std: 0, phase: '' }; }
function startAnalysis() { /* Placeholder */ }
function drawChart() { /* Placeholder */ }
function connectAPI() { /* Placeholder */ }
function showSpinner(text) { elements.spinner.classList.remove('hidden'); elements.progressText.textContent = text || 'Обработка...'; }
function hideSpinner() { elements.spinner.classList.add('hidden'); elements.progressText.textContent = ''; }
function showAnalysisResult(text) { elements.llmText.textContent = text; elements.llmOutput.classList.remove('hidden'); }
function copyReport() {
  const text = elements.llmText.textContent;
  navigator.clipboard.writeText(text).then(() => {
    showAlert('Отчет скопирован в буфер обмена', 'success');
  }).catch(err => {
    showAlert(`Ошибка копирования: ${err.message}`, 'error');
  });
}
function saveReport() { /* Placeholder */ }
function sendReport() { /* Placeholder */ }
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