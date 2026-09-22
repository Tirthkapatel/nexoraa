const API_URL = '/api';

// --- 3D Hero Setup ---
function init3D() {
    const container = document.getElementById('three-container');
    if (!container) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.z = 10;
    camera.position.x = 2;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Data Core Object
    const coreGeometry = new THREE.IcosahedronGeometry(2, 1);
    const coreMaterial = new THREE.MeshPhysicalMaterial({
        color: 0xA9435A, // Primary
        emissive: 0x2A1B20,
        wireframe: true,
        transparent: true,
        opacity: 0.8,
        roughness: 0.2,
        metalness: 0.8
    });
    
    const core = new THREE.Mesh(coreGeometry, coreMaterial);
    scene.add(core);

    // Inner glowing core
    const innerGeo = new THREE.IcosahedronGeometry(1.2, 0);
    const innerMat = new THREE.MeshBasicMaterial({ color: 0xF29B82, wireframe: true, transparent: true, opacity: 0.3 });
    const innerCore = new THREE.Mesh(innerGeo, innerMat);
    core.add(innerCore);

    // Particles
    const particleCount = 150;
    const particlesGeo = new THREE.BufferGeometry();
    const posArray = new Float32Array(particleCount * 3);
    
    for(let i=0; i<particleCount*3; i++) {
        posArray[i] = (Math.random() - 0.5) * 12;
    }
    particlesGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const particlesMat = new THREE.PointsMaterial({
        size: 0.05,
        color: 0xF29B82,
        transparent: true,
        opacity: 0.6
    });
    const particlesMesh = new THREE.Points(particlesGeo, particlesMat);
    scene.add(particlesMesh);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    const pointLight = new THREE.PointLight(0xF29B82, 2);
    pointLight.position.set(5, 5, 5);
    scene.add(pointLight);

    // Interaction
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;
    
    document.addEventListener('mousemove', (e) => {
        mouseX = (e.clientX / window.innerWidth) * 2 - 1;
        mouseY = -(e.clientY / window.innerHeight) * 2 + 1;
    });

    const clock = new THREE.Clock();

    function animate() {
        requestAnimationFrame(animate);
        const elapsedTime = clock.getElapsedTime();

        // Rotate core
        core.rotation.y += 0.002;
        core.rotation.x += 0.001;
        
        innerCore.rotation.y -= 0.003;
        innerCore.rotation.z += 0.002;

        // Float effect
        core.position.y = Math.sin(elapsedTime * 0.5) * 0.2;

        // Particles slow rotation
        particlesMesh.rotation.y = elapsedTime * 0.05;

        // Mouse interaction (parallax)
        targetX = mouseX * 0.5;
        targetY = mouseY * 0.5;
        
        core.rotation.y += 0.05 * (targetX - core.rotation.y);
        core.rotation.x += 0.05 * (targetY - core.rotation.x);

        renderer.render(scene, camera);
    }
    
    animate();

    window.addEventListener('resize', () => {
        if(!container) return;
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });
    
    // Export function to speed up on load
    window.pulse3D = () => {
        coreMaterial.color.setHex(0xF29B82);
        setTimeout(() => coreMaterial.color.setHex(0xA9435A), 500);
    };
}

// --- Number Animation Setup ---
function setupNumberAnimations() {
    window.numberObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if(entry.isIntersecting) {
                const el = entry.target;
                if(!el.classList.contains('animated')) {
                    el.classList.add('animated');
                    startCounterAnimation(el);
                }
            }
        });
    }, { threshold: 0.1 });
}

function startCounterAnimation(el) {
    const targetVal = parseFloat(el.getAttribute('data-val'));
    if(isNaN(targetVal)) return;
    
    const duration = 1500;
    let startTimestamp = null;
    const isFloat = el.getAttribute('data-float') === 'true';
    
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
        const currentVal = easeProgress * targetVal;
        
        el.innerText = isFloat ? currentVal.toFixed(2) : Math.floor(currentVal).toLocaleString();
        
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            el.innerText = isFloat ? targetVal.toFixed(2) : targetVal.toLocaleString();
        }
    };
    window.requestAnimationFrame(step);
}

// --- Navigation ---
function setupNav() {
    const links = document.querySelectorAll('.nav-links a');
    const sections = document.querySelectorAll('.dash-section');
    
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('data-target');
            
            // Update nav state
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // Update sections
            sections.forEach(s => s.classList.remove('active-section'));
            document.getElementById(targetId).classList.add('active-section');
            
            // Trigger plotly resize if charts are shown
            if(targetId === 'viz-section') {
                window.dispatchEvent(new Event('resize'));
            }
        });
    });

    document.getElementById('clear-btn').addEventListener('click', () => {
        currentDataset = null;
        document.getElementById('dashboard').style.display = 'none';
        document.getElementById('main-nav').style.display = 'none';
        document.getElementById('hero-section').style.display = 'flex';
        document.getElementById('upload-status').innerText = '';
    });
}

// --- Global State ---
let currentDataset = null;

// --- Upload Logic ---
function setupUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-upload');
    const demoBtn = document.getElementById('demo-btn');
    const statusMsg = document.getElementById('upload-status');
    const defaultState = document.getElementById('upload-default-state');
    const loadingState = document.getElementById('upload-loading-state');
    
    function showLoading() {
        defaultState.style.display = 'none';
        loadingState.style.display = 'block';
    }
    
    function hideLoading() {
        defaultState.style.display = 'block';
        loadingState.style.display = 'none';
    }
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });
    
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if(dt.files.length) handleFiles(dt.files[0]);
    });
    
    fileInput.addEventListener('change', function() {
        if(this.files.length) handleFiles(this.files[0]);
    });
    
    demoBtn.addEventListener('click', () => {
        statusMsg.className = 'status-msg';
        statusMsg.innerText = 'Loading demo dataset...';
        if(window.pulse3D) window.pulse3D();
        showLoading();
        
        const startTime = Date.now();
        
        fetch(`${API_URL}/demo`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                const elapsed = Date.now() - startTime;
                const delay = Math.max(0, 1500 - elapsed);
                setTimeout(() => {
                    hideLoading();
                    if(data.overview) {
                        currentDataset = data;
                        loadDashboard();
                    } else throw new Error(data.detail || "Error loading demo");
                }, delay);
            })
            .catch(err => {
                hideLoading();
                statusMsg.className = 'status-msg error';
                statusMsg.innerText = err.message;
            });
    });
    
    function handleFiles(file) {
        if(!file.name.match(/\.(csv|xlsx)$/i)) {
            statusMsg.className = 'status-msg error';
            statusMsg.innerText = 'Invalid file type. Please upload a CSV or XLSX.';
            return;
        }
        
        statusMsg.className = 'status-msg';
        statusMsg.innerText = `Uploading ${file.name}...`;
        if(window.pulse3D) window.pulse3D();
        showLoading();
        
        const formData = new FormData();
        formData.append('file', file);
        
        const startTime = Date.now();
        
        fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        })
        .then(res => {
            if(!res.ok) throw res;
            return res.json();
        })
        .then(data => {
            const elapsed = Date.now() - startTime;
            const delay = Math.max(0, 1500 - elapsed);
            setTimeout(() => {
                hideLoading();
                currentDataset = data;
                loadDashboard();
            }, delay);
        })
        .catch(async err => {
            hideLoading();
            let msg = 'Upload failed.';
            if(err.json) {
                const e = await err.json();
                msg = e.detail || msg;
            }
            statusMsg.className = 'status-msg error';
            statusMsg.innerText = msg;
        });
    }
}

// --- Data Loading & UI Population ---
async function loadDashboard() {
    try {
        document.getElementById('hero-section').style.display = 'none';
        document.getElementById('dashboard').style.display = 'block';
        document.getElementById('main-nav').style.display = 'flex';
        
        populateOverview(currentDataset, currentDataset.preview);
        populateAnalysis(currentDataset.analysis);
        renderCharts(currentDataset.viz);
        
        generateInsights();
        document.querySelector('.nav-links a[data-target="overview-section"]').click();
        
    } catch (err) {
        console.error(err);
        alert("Failed to load dashboard data.");
    }
}

function populateOverview(info, previewData) {
    const ov = info.overview;
    
    // Header
    document.getElementById('dh-filename').innerText = info.filename;
    
    const setMetric = (id, val) => {
        const el = document.getElementById(id);
        el.innerText = '0';
        el.classList.add('animate-num');
        el.classList.remove('animated'); // reset if already animated
        el.setAttribute('data-val', val);
        el.setAttribute('data-float', 'false');
        if(window.numberObserver) window.numberObserver.observe(el);
    };

    setMetric('dh-rows', ov.row_count);
    setMetric('dh-cols', ov.column_count);
    
    const totalMissing = Object.values(ov.missing_values).reduce((a,b)=>a+b,0);
    setMetric('dh-missing', totalMissing);
    setMetric('dh-dupes', ov.duplicate_rows);
    
    // Preview Table
    const tHead = document.querySelector('#preview-table thead');
    const tBody = document.querySelector('#preview-table tbody');
    tHead.innerHTML = ''; tBody.innerHTML = '';
    
    if(previewData.length > 0) {
        const cols = Object.keys(previewData[0]);
        let hr = '<tr>';
        cols.forEach(c => hr += `<th>${c}</th>`);
        hr += '</tr>';
        tHead.innerHTML = hr;
        
        previewData.forEach(row => {
            let tr = '<tr>';
            cols.forEach(c => tr += `<td>${row[c] !== null ? row[c] : '<em>NaN</em>'}</td>`);
            tr += '</tr>';
            tBody.innerHTML += tr;
        });
    }
    
    // Types list
    const typeList = document.getElementById('col-types-list');
    typeList.innerHTML = '';
    Object.entries(ov.dtypes).forEach(([col, type]) => {
        typeList.innerHTML += `<li><span>${col}</span> <span>${type}</span></li>`;
    });
    
    // Quality list
    const qList = document.getElementById('data-quality-list');
    qList.innerHTML = '';
    let hasIssues = false;
    if(totalMissing > 0) {
        qList.innerHTML += `<li><span>Missing Values</span> <span>${totalMissing} cells</span></li>`;
        hasIssues = true;
    }
    if(ov.duplicate_rows > 0) {
        qList.innerHTML += `<li><span>Duplicate Rows</span> <span>${ov.duplicate_rows} rows</span></li>`;
        hasIssues = true;
    }
    if(!hasIssues) {
        qList.innerHTML = `<li><span>All checks passed</span> <span>Clean dataset</span></li>`;
    }
    
    // Prepare Report
    document.getElementById('report-filename').innerText = info.filename;
    document.getElementById('report-quality-list').innerHTML = qList.innerHTML;
}

function populateAnalysis(analysis) {
    // Numerical
    const numTbody = document.querySelector('#num-stats-table tbody');
    numTbody.innerHTML = '';
    Object.entries(analysis.numerical).forEach(([col, stats]) => {
        if(stats.count > 0) {
            numTbody.innerHTML += `<tr>
                <td><strong>${col}</strong></td>
                <td><span class="animate-num" data-val="${stats.count}" data-float="false">0</span></td>
                <td><span class="animate-num" data-val="${stats.mean}" data-float="true">0.00</span></td>
                <td><span class="animate-num" data-val="${stats.median}" data-float="true">0.00</span></td>
                <td><span class="animate-num" data-val="${stats.min}" data-float="true">0.00</span></td>
                <td><span class="animate-num" data-val="${stats.max}" data-float="true">0.00</span></td>
                <td><span class="animate-num" data-val="${stats.std}" data-float="true">0.00</span></td>
            </tr>`;
        }
    });
    
    // Categorical
    const catTbody = document.querySelector('#cat-stats-table tbody');
    catTbody.innerHTML = '';
    Object.entries(analysis.categorical).forEach(([col, stats]) => {
        if(stats.unique_count > 0) {
            let topVal = stats.top_values[0] || '-';
            let topFreq = stats.frequencies[0] || 0;
            catTbody.innerHTML += `<tr>
                <td><strong>${col}</strong></td>
                <td><span class="animate-num" data-val="${stats.unique_count}" data-float="false">0</span></td>
                <td>${topVal} (<span class="animate-num" data-val="${topFreq}" data-float="false">0</span>)</td>
            </tr>`;
        }
    });
    
    // Attach observer to new elements
    setTimeout(() => {
        if(window.numberObserver) {
            document.querySelectorAll('#stats-section .animate-num').forEach(el => {
                window.numberObserver.observe(el);
            });
        }
    }, 100);
}

function renderCharts(vizData) {
    const layoutBase = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: '#FFF7F2', family: 'Inter', size: 12 },
        title: { font: { family: 'Playfair Display', size: 18, color: '#F29B82' }, pad: { b: 20 } },
        colorway: ['#A9435A', '#F29B82', '#E06C75'],
        margin: { t: 60, l: 50, r: 30, b: 50 },
        xaxis: {
            gridcolor: 'rgba(255, 247, 242, 0.05)',
            zerolinecolor: 'rgba(255, 247, 242, 0.1)',
            tickfont: { color: 'rgba(255, 247, 242, 0.6)' },
            titlefont: { color: 'rgba(255, 247, 242, 0.6)' }
        },
        yaxis: {
            gridcolor: 'rgba(255, 247, 242, 0.05)',
            zerolinecolor: 'rgba(255, 247, 242, 0.1)',
            tickfont: { color: 'rgba(255, 247, 242, 0.6)' },
            titlefont: { color: 'rgba(255, 247, 242, 0.6)' }
        },
        bargap: 0.2,
        hovermode: 'closest',
        hoverlabel: { bgcolor: '#1C1215', font: { family: 'Inter', color: '#FFF7F2' } }
    };

    if(vizData.bar) {
        Plotly.newPlot('chart-bar', [{
            x: vizData.bar.x,
            y: vizData.bar.y,
            type: 'bar',
            marker: { 
                color: '#A9435A',
                line: { color: 'rgba(255,255,255,0.1)', width: 1 }
            }
        }], { ...layoutBase, title: { text: vizData.bar.title } }, {responsive: true, displayModeBar: false});
    } else {
        document.getElementById('chart-bar').innerHTML = '<div style="padding:20px;text-align:center;color:#666;">Not enough categorical data</div>';
    }

    if(vizData.histogram) {
        Plotly.newPlot('chart-hist', [{
            x: vizData.histogram.x,
            type: 'histogram',
            marker: { 
                color: '#F29B82',
                line: { color: 'rgba(255,255,255,0.1)', width: 1 }
            }
        }], { ...layoutBase, title: { text: vizData.histogram.title } }, {responsive: true, displayModeBar: false});
    }
    
    if(vizData.scatter) {
        Plotly.newPlot('chart-scatter', [{
            x: vizData.scatter.x,
            y: vizData.scatter.y,
            mode: 'markers',
            type: 'scatter',
            marker: { color: '#F29B82', size: 8, opacity: 0.7, line: { color: '#FFF7F2', width: 0.5 } }
        }], { 
            ...layoutBase, 
            title: { text: vizData.scatter.title },
            xaxis: { ...layoutBase.xaxis, title: { text: vizData.scatter.x_col } },
            yaxis: { ...layoutBase.yaxis, title: { text: vizData.scatter.y_col } }
        }, {responsive: true, displayModeBar: false});
    } else {
        document.getElementById('chart-scatter').innerHTML = '<div style="padding:20px;text-align:center;color:#666;">Not enough numerical columns for scatter plot</div>';
    }
}

async function generateInsights() {
    const contentDiv = document.getElementById('ai-insights-content');
    const reportDiv = document.getElementById('report-insights');
    
    contentDiv.innerHTML = '<div class="loading-spinner">Generating insights...</div>';
    
    try {
        const payload = {
            summary: {
                overview: currentDataset.overview,
                analysis: currentDataset.analysis
            }
        };
        const res = await fetch(`${API_URL}/insights`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        const text = data.insights || "No insights available.";
        contentDiv.innerText = text;
        reportDiv.innerText = text;
        document.getElementById('report-summary-text').innerText = "Dataset processed and analyzed successfully. See insights below.";
    } catch(err) {
        contentDiv.innerHTML = '<span style="color:#ff6b6b">Failed to generate insights.</span>';
    }
}

// --- Chat Setup ---
function setupChat() {
    const input = document.getElementById('chat-input');
    const btn = document.getElementById('chat-send-btn');
    const history = document.getElementById('chat-history');
    
    const sendMsg = async () => {
        const q = input.value.trim();
        if(!q || !currentDataset) return;
        
        // Add user msg
        history.innerHTML += `<div class="chat-msg user">${q}</div>`;
        input.value = '';
        history.scrollTop = history.scrollHeight;
        
        // Add loading sys msg
        const loaderId = 'msg-' + Date.now();
        history.innerHTML += `<div class="chat-msg system" id="${loaderId}">Thinking...</div>`;
        history.scrollTop = history.scrollHeight;
        
        try {
            const payload = {
                question: q,
                summary: {
                    overview: currentDataset.overview,
                    analysis: currentDataset.analysis
                }
            };
            const res = await fetch(`${API_URL}/ask`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            document.getElementById(loaderId).innerText = data.answer;
        } catch(err) {
            document.getElementById(loaderId).innerText = "Sorry, I encountered an error answering that.";
        }
    };
    
    btn.addEventListener('click', sendMsg);
    input.addEventListener('keypress', (e) => {
        if(e.key === 'Enter') sendMsg();
    });
    
    document.getElementById('regen-insights-btn').addEventListener('click', () => {
        if(currentDataset) generateInsights();
    });
}

// Init
window.onload = () => {
    setupNumberAnimations();
    init3D();
    setupNav();
    setupUpload();
    setupChat();
};
