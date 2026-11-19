@echo off
setlocal

REM Inicia a aplicacao Flask do projeto ProjetoCodex.
set "PROJECT_DIR=%~dp0ProjetoCodex"
set "VENV_PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "FLASK_EXE=%PROJECT_DIR%\.venv\Scripts\flask.exe"

if not exist "%PROJECT_DIR%" (
    echo ERRO: pasta ProjetoCodex nao encontrada ao lado deste arquivo.
    pause
    exit /b 1
)

if not exist "%VENV_PYTHON%" (
    echo ERRO: ambiente virtual nao encontrado em ProjetoCodex\.venv.
    echo Consulte o README.md para preparar o projeto pela primeira vez.
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%\.env" (
    echo ERRO: arquivo ProjetoCodex\.env nao encontrado.
    echo Crie-o copiando ProjetoCodex\.env.example e configure as chaves secretas.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"
echo Iniciando a aplicacao em http://127.0.0.1:5000
echo Para encerrar, pressione Ctrl+C nesta janela.
echo.
"%FLASK_EXE%" --app run.py run --debug --host 127.0.0.1 --port 5000

if errorlevel 1 (
    echo.
    echo A aplicacao foi encerrada com erro. Verifique a mensagem acima.
    pause
)

endlocal
