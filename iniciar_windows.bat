@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Preparando o projeto. Isso so precisa ser feito na primeira vez.
    py -3 -m venv .venv
    if errorlevel 1 goto falha
)
if not exist ".venv\dependencias_prontas.txt" (
    echo Baixando as bibliotecas. Aguarde com a internet conectada.
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 goto falha
    echo Instalado > .venv\dependencias_prontas.txt
)
echo Quando aparecer "Painel disponivel", abra http://127.0.0.1:5000 no navegador.
echo Deixe esta janela aberta enquanto usa o painel. Para encerrar, pressione Ctrl+C.
.venv\Scripts\python.exe app.py
pause
exit /b
:falha
echo Nao foi possivel preparar o projeto.
echo Confira se o Python 3.11 ou 3.12 esta instalado e se a internet esta funcionando.
echo Os comandos para instalar manualmente estao no README.md.
pause
