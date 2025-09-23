// main.js - VERSAÃO QUE FUNCIONA
const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const net = require('net');

let janela;
let pythonProcess;

// Função que espera o Python ficar pronto
function esperarPython(callback) {
    console.log('⏳ Aguardando Python iniciar...');
    
    function tentarConectar(tentativa = 1) {
        const client = net.connect({ port: 5000 }, () => {
            console.log('Python está pronto!');
            client.end();
            callback(true);
        });
        
        client.on('error', (err) => {
            if (tentativa < 10) {
                console.log(`Tentativa ${tentativa}/10 - Python ainda não está pronto...`);
                setTimeout(() => tentarConectar(tentativa + 1), 1000);
            } else {
                console.log('Python não iniciou após 10 tentativas');
                callback(false);
            }
        });
    }
    
    tentarConectar();
}

app.whenReady().then(() => {
    console.log('Iniciando backend Python...');
    
    // Iniciar o processo Python
    pythonProcess = spawn('python', ['backend.py']);
    
    // Capturar logs do Python
    pythonProcess.stdout.on('data', (data) => {
        console.log(`Python: ${data}`);
    });
    
    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python Error: ${data}`);
    });
    
    // Esperar Python ficar pronto antes de abrir a janela
    esperarPython((sucesso) => {
        if (sucesso) {
            criarJanela();
        } else {
            console.log('Abrindo janela mesmo com Python offline...');
            criarJanela();
        }
    });
});

function criarJanela() {
    janela = new BrowserWindow({
        width: 600,
        height: 400,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });
    
    janela.loadFile('index.html');
    console.log('Janela do Electron aberta!');
}

// Fechar Python quando Electron fechar
app.on('window-all-closed', () => {
    console.log('Fechando aplicação...');
    if (pythonProcess) {
        pythonProcess.kill();
        console.log('Processo Python finalizado');
    }
    app.quit();
});

// Tratar erros no processo Python
pythonProcess?.on('error', (err) => {
    console.error('Erro ao iniciar Python:', err);
});