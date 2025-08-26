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

    // Prepare time index
    const indices = data.map((_, i) => i);

    // Determine the primary defect (assuming consistent across data)
    const primaryDefect = data[0].defect || 'Unknown';

    // Chart 1: Severity Metric (K_value) over Time with threshold lines
    const kValues = data.map(row => parseFloat(row['K_value']));
    const traceK = {
      x: indices,
      y: kValues,
      mode: 'lines+markers',
      name: 'K_value (Severity Metric)',
      type: 'scatter',
      line: { color: '#FF4F12', width: 2 }
    };

    // Threshold lines
    const lowThreshold = { type: 'line', x0: 0, x1: Math.max(...indices), y0: 2.0, y1: 2.0, line: { color: '#2ecc71', dash: 'dash', width: 1 }, name: 'Low Threshold' };
    const medThreshold = { type: 'line', x0: 0, x1: Math.max(...indices), y0: 4.0, y1: 4.0, line: { color: '#f1c40f', dash: 'dash', width: 1 }, name: 'Medium Threshold' };
    const highThreshold = { type: 'line', x0: 0, x1: Math.max(...indices), y0: 6.0, y1: 6.0, line: { color: '#FF4F12', dash: 'dash', width: 1 }, name: 'High Threshold' };

    Plotly.newPlot(chart1.id, [traceK], {
      title: 'Метрика Тяжести (K_value) во Времени',
      xaxis: { title: 'Индекс Временного Окна' },
      yaxis: { title: 'Значение K' },
      shapes: [lowThreshold, medThreshold, highThreshold],
      margin: { t: 50 }
    });

    // Chart 2: Bearing Defect Scores over Time (f1: Inner Race, f2: Outer Race, f3: Ball, f4: Cage)
    // Relevant for bearing defects; highlight if primary defect is bearing-related
    const traceF1 = { x: indices, y: data.map(row => parseFloat(row['f1'])), mode: 'lines', name: 'Inner Race Score (f1)', line: { color: primaryDefect === 'Inner Race' ? '#FF4F12' : '#ffffff', width: primaryDefect === 'Inner Race' ? 3 : 1 } };
    const traceF2 = { x: indices, y: data.map(row => parseFloat(row['f2'])), mode: 'lines', name: 'Outer Race Score (f2)', line: { color: primaryDefect === 'Outer Race' ? '#FF4F12' : '#ffffff', width: primaryDefect === 'Outer Race' ? 3 : 1 } };
    const traceF3 = { x: indices, y: data.map(row => parseFloat(row['f3'])), mode: 'lines', name: 'Ball Score (f3)', line: { color: primaryDefect === 'Ball' ? '#FF4F12' : '#ffffff', width: primaryDefect === 'Ball' ? 3 : 1 } };
    const traceF4 = { x: indices, y: data.map(row => parseFloat(row['f4'])), mode: 'lines', name: 'Cage Score (f4)', line: { color: primaryDefect === 'Cage' ? '#FF4F12' : '#ffffff', width: primaryDefect === 'Cage' ? 3 : 1 } };

    // Family threshold line (FAMILY_T = 0.0, but for visibility, show at a reasonable detection level if needed)
    const familyThreshold = { type: 'line', x0: 0, x1: Math.max(...indices), y0: 0.0, y1: 0.0, line: { color: '#f1c40f', dash: 'dash', width: 1 }, name: 'Detection Threshold' };

    Plotly.newPlot(chart2.id, [traceF1, traceF2, traceF3, traceF4], {
      title: 'Оценки Дефектов Подшипника во Времени',
      xaxis: { title: 'Индекс Временного Окна' },
      yaxis: { title: 'Оценка Дефекта' },
      shapes: [familyThreshold],
      margin: { t: 50 }
    });

    // Chart 3: Rotor/Misalignment/Imbalance Related Features (f5: MCSA Shaft Sidebands, f26: Envelope Slope)
    // Highlight f5 for Rotor/Imbalance/Misalignment
    const traceF5 = { x: indices, y: data.map(row => parseFloat(row['f5'])), mode: 'lines', name: 'MCSA Shaft Sidebands (f5)', line: { color: ['Rotor', 'Imbalance', 'Misalignment'].includes(primaryDefect) ? '#FF4F12' : '#ffffff', width: ['Rotor', 'Imbalance', 'Misalignment'].includes(primaryDefect) ? 3 : 1 } };
    const traceF26 = { x: indices, y: data.map(row => parseFloat(row['f26'])), mode: 'lines', name: 'Envelope Spectrum Slope (f26)', line: { color: '#2ecc71' } };

    // Additional highlight lines (e.g., for rotor SNR threshold ~5.0 from ROTOR_SNR_T)
    const rotorSNRThreshold = { type: 'line', x0: 0, x1: Math.max(...indices), y0: 5.0, y1: 5.0, line: { color: '#f1c40f', dash: 'dash', width: 1 }, name: 'Rotor SNR Threshold' };

    Plotly.newPlot(chart3.id, [traceF5, traceF26], {
      title: 'Признаки, Связанные с Ротором/Расцентровкой/Дисбалансом',
      xaxis: { title: 'Индекс Временного Окна' },
      yaxis: { title: 'Значение Признака' },
      shapes: [rotorSNRThreshold],
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