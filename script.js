// Navegação entre páginas
document.addEventListener('DOMContentLoaded', function() {
    // Configura os listeners dos links do menu
    document.querySelectorAll('.sidebar-nav a[data-page]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.getAttribute('data-page');
            loadPage(page);
            
            // Atualiza menu selecionado
            updateSelectedMenu(this);
        });
    });
    
    // Carrega a página inicial (Home) por padrão
    loadPage('home');
    updateSelectedMenu(document.querySelector('a[data-page="home"]'));
});

function updateSelectedMenu(selectedLink) {
    document.querySelectorAll('.sidebar-nav li').forEach(li => {
        li.classList.remove('selected');
    });
    selectedLink.parentElement.classList.add('selected');
}

async function loadPage(pageName) {
    try {
        const response = await fetch(`pages/${pageName}.html`);
        
        if (!response.ok) {
            throw new Error('Página não encontrada');
        }
        
        const html = await response.text();
        document.getElementById('page-container').innerHTML = html;
        document.querySelector('.page-title').textContent = getPageTitle(pageName);
        
        // Configura eventos específicos da página carregada
        setupPageEvents(pageName);
        
    } catch (error) {
        console.error('Erro ao carregar página:', error);
        document.getElementById('page-container').innerHTML = 
            '<div class="page-content"><p>Erro ao carregar a página.</p></div>';
    }
}

function setupPageEvents(pageName) {
    if (pageName === 'registro') {
        setupRegistroPage();
    }
}

// CONFIGURA A PÁGINA DE REGISTRO
function setupRegistroPage() {
    const btnAnalisar = document.getElementById('btn-analisar');
    
    if (btnAnalisar) {
        btnAnalisar.addEventListener('click', analisarProduto);
    }
    
    // Enter no input também submete
    const urlInput = document.getElementById('url');
    if (urlInput) {
        urlInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                analisarProduto();
            }
        });
    }
}

// FUNÇÃO PRINCIPAL PARA ANALISAR PRODUTO
async function analisarProduto() {
    const url = document.getElementById('url')?.value;
    document.getElementById("form-link").style.display = "none";

    if (!url) {
        mostrarResultado('error', 'Cole a URL do produto Amazon!');
        return;
    }
    
    // Validação básica de URL
    if (!url.includes('amazon.com.br') || !url.includes('/dp/')) {
        mostrarResultado('error', 'URL da Amazon inválida. Deve ser um link de produto Amazon.com.br');
        return;
    }
    
    try {
        mostrarResultado('processing', 'Iniciando análise do produto...');
        
        const response = await fetch('http://localhost:5000/registro', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        
        const data = await response.json();
        
        if (response.ok && data.sucesso) {
            mostrarResultado('success', 
                `Análise iniciada com sucesso!<br>
                 <strong>URL:</strong> ${data.url_recebida}<br>
                 <strong>ID:</strong> ${data.process_id}<br>
                 <strong>Status:</strong> ${data.status}`,
                data.process_id
            );
            
            // Iniciar monitoramento em tempo real
            monitorarProcessamento(data.process_id, data.url_recebida);
            
        } else {
            mostrarResultado('error', `Erro: ${data.erro}`);
        }
        
    } catch (error) {
        mostrarResultado('error', 'Erro de conexão com o servidor. Verifique se o backend está rodando.');
        console.error('Erro:', error);
    }
}

// FUNÇÃO PARA MOSTRAR RESULTADOS COM VISUAL MELHORADO
function mostrarResultado(tipo, mensagem, processId = null) {
    const resultadoDiv = document.getElementById('resultado');
    
    const icones = {
        success: '✅',
        error: '❌',
        processing: '⏳',
        info: 'ℹ️'
    };
    
    const classes = {
        success: 'resultado-sucesso',
        error: 'resultado-erro',
        processing: 'resultado-processando',
        info: 'resultado-processando'
    };
    
    const titulos = {
        success: 'Sucesso!',
        error: 'Erro!',
        processing: 'Processando...',
        info: 'Informação'
    };
    
    resultadoDiv.innerHTML = `
        <div class="resultado-container ${classes[tipo]}">
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <span class="status-icon">${icones[tipo]}</span>
                <strong style="font-size: 1.1em;">${titulos[tipo]}</strong>
            </div>
            <div style="margin-bottom: 15px;">${mensagem}</div>
            ${tipo === 'processing' ? '<div class="loading-dots"></div>' : ''}
            ${processId ? `
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
                </div>
                <div id="etapa-atual" style="margin-top: 10px; font-size: 0.9em; color: var(--text-medium);">
                    <strong>Iniciando...</strong><br>
                    <small>Aguardando progresso</small>
                </div>
            ` : ''}
        </div>
    `;
}

// MONITORAMENTO EM TEMPO REAL COM PROGRESSO REAL
async function monitorarProcessamento(processId, url) {
    let ultimaAtualizacao = Date.now();
    let tentativasConsecutivas = 0;
    
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`http://localhost:5000/status/${processId}`);
            const status = await response.json();
            
            if (status.erro) {
                clearInterval(interval);
                mostrarResultado('error', `Processo não encontrado: ${processId}`);
                return;
            }
            
            // Atualiza UI com progresso real
            atualizarProgressoReal(status);
            ultimaAtualizacao = Date.now();
            tentativasConsecutivas = 0;
            
            if (status.status === 'concluido') {
                clearInterval(interval);
                mostrarResultadoConcluido(status);
            } else if (status.status === 'erro') {
                clearInterval(interval);
                mostrarResultadoErro(status);
            }
            
        } catch (error) {
            console.error('Erro ao verificar status:', error);
            tentativasConsecutivas++;
            
            // Se várias tentativas falharem, considera erro
            if (tentativasConsecutivas > 3 || Date.now() - ultimaAtualizacao > 30000) {
                clearInterval(interval);
                mostrarResultado('error', 'Conexão perdida com o servidor');
            }
        }
    }, 1500); // Atualiza a cada 1.5 segundos

    // Timeout de segurança (10 minutos)
    setTimeout(() => {
        clearInterval(interval);
        if (!document.querySelector('.resultado-sucesso')) {
            mostrarResultado('error', 'Tempo limite excedido (10 minutos). O processamento pode ter encontrado problemas.');
        }
    }, 600000);
}

function atualizarProgressoReal(status) {
    const progressFill = document.getElementById('progress-fill');
    const etapaElement = document.getElementById('etapa-atual');
    
    if (progressFill) {
        progressFill.style.width = `${status.progresso}%`;
        progressFill.style.transition = 'width 0.5s ease';
        
        // Muda cor baseada no progresso
        if (status.progresso < 30) {
            progressFill.style.background = '#ef4444'; // vermelho
        } else if (status.progresso < 70) {
            progressFill.style.background = '#f59e0b'; // laranja
        } else {
            progressFill.style.background = '#10b981'; // verde
        }
    }
    
    if (etapaElement) {
        etapaElement.innerHTML = `
            <strong>${status.etapa_atual}</strong><br>
            <small>Progresso: ${status.progresso}% • ${status.timestamp_lega || ''}</small>
        `;
        
        // Adiciona ícone baseado no progresso
        let icone = '⏳';
        if (status.progresso > 90) icone = '✅';
        else if (status.progresso > 50) icone = '⚡';
        
        etapaElement.innerHTML = `
            <strong>${icone} ${status.etapa_atual}</strong><br>
            <small>Progresso: ${status.progresso}% • ${status.timestamp_lega || ''}</small>
        `;
    }
}

function mostrarResultadoConcluido(status) {
    const resultadoDiv = document.getElementById('resultado');
    resultadoDiv.innerHTML = `
        <div class="resultado-container resultado-sucesso">
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <span class="status-icon">🎉</span>
                <strong style="font-size: 1.1em;">Processamento Concluído!</strong>
            </div>
            <div style="margin-bottom: 15px;">
                <strong>✅ Tarefa finalizada com sucesso!</strong><br><br>
                <strong>Arquivos gerados:</strong><br>
                • amazon_product.csv<br>
                • amazon_reviews.csv<br><br>
                <strong>Etapa final:</strong> ${status.etapa_atual}<br>
                <strong>Concluído em:</strong> ${status.timestamp_lega || new Date().toLocaleTimeString()}
            </div>
            <div style="background: rgba(16, 185, 129, 0.1); padding: 10px; border-radius: 5px; border-left: 3px solid #10b981; margin-top: 15px;">
                <small>✅ Os arquivos foram salvos na pasta do projeto.<br>
                ✅ Você pode fechar esta página ou iniciar uma nova análise.</small>
            </div>
            <button onclick="analisarProduto()" class="submit-button" style="margin-top: 15px; width: 100%;">
                🔄 Analisar Outro Produto
            </button>
        </div>
    `;
}

function mostrarResultadoErro(status) {
    const resultadoDiv = document.getElementById('resultado');
    resultadoDiv.innerHTML = `
        <div class="resultado-container resultado-erro">
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <span class="status-icon">❌</span>
                <strong style="font-size: 1.1em;">Erro no Processamento</strong>
            </div>
            <div style="margin-bottom: 15px;">
                <strong>Ocorreu um erro durante a execução:</strong><br><br>
                <strong>Detalhes:</strong> ${status.etapa_atual}<br>
                <strong>Hora do erro:</strong> ${status.timestamp_lega || new Date().toLocaleTimeString()}
            </div>
            <div style="background: rgba(239, 68, 68, 0.1); padding: 10px; border-radius: 5px; border-left: 3px solid #ef4444; margin-bottom: 15px;">
                <small>💡 Tente novamente ou verifique a URL do produto.<br>
                🔄 Se o problema persistir, reinicie o servidor backend.</small>
            </div>
            <button onclick="location.reload()" class="submit-button" style="width: 100%;">
                🔄 Tentar Novamente
            </button>
        </div>
    `;
}

function getPageTitle(page) {
    const titles = {
        'home': 'Página Principal',
        'data-analysis': 'Análise de Dados',
        'reports': 'Relatórios',
        'registro': 'Análise de Produto Amazon',
        'settings': 'Configurações'
    };
    return titles[page] || 'Página';
}