# GUY Builder

> **Python → EXE. Simplificado.**

O **GUY Builder** é uma interface gráfica (e uma CLI) para empacotar aplicações Python em executáveis Windows usando o [PyInstaller](https://pyinstaller.org/). Ele cuida de localizar o Python certo, verificar dependências, empacotar em uma área temporária, publicar o `.exe` na pasta de saída e explicar o que deu errado quando algo falha.

```text
Código Python ──► GUY Builder ──► área temporária ──► .exe final (independente)
                       │
                       └─ usa um Python REAL + PyInstaller (nunca o próprio .exe do builder)
```

## Recursos

- **Arquivo ou projeto**: selecione um `.py` avulso ou a pasta de um projeto (detecção de `main.py`, `app.py`, `run.py`...).
- **Dependências**: segue os imports locais a partir do entrypoint e confere, no Python que fará o build, se os pacotes de terceiros estão instalados — *antes* de empacotar.
- **Opções**: nome do EXE, ícone `.ico`, console ou janela, arquivo único ou pasta, imports extras, arquivos/pastas adicionais (`--add-data`), pasta de saída.
- **Independência**: o executável gerado não referencia o builder, o `dist` anterior, nem caminhos da máquina de desenvolvimento. O build acontece em uma pasta temporária própria, removida ao final.
- **Self-build**: o GUY Builder compila a si mesmo e o `.exe` resultante compila outros programas.
- **Erros claros**: cada falha informa etapa, comando executado, mensagem e possível solução.
- **Log estilo terminal**, barra de progresso por etapa, cancelamento (encerra a árvore de processos) e botão *Copiar log*.
- **Conversor PNG → ICO**: preview do PNG, escolha das resoluções (16–256 px), preview do `.ico` com todas as resoluções sobre fundo xadrez (mostra transparência), informações da imagem e botão *Usar como ícone do build*.
- **Modo CLI** para automação e testes.

## Requisitos

| Ambiente | Precisa de |
|---|---|
| Máquina que **gera** o EXE | Windows, **Python 3.8+ instalado**, PyInstaller e as dependências do projeto alvo |
| Máquina que **executa** o EXE | Normalmente nada (Python é embutido pelo PyInstaller) |

> **Importante:** mesmo o `GUY Builder.exe` precisa de um Python instalado na máquina para compilar *outros* programas. O PyInstaller só empacota corretamente um projeto se rodar no Python onde as dependências desse projeto estão instaladas — por isso o builder não embute um interpretador próprio.

O PyInstaller pode ser instalado pela própria interface (com confirmação) ou manualmente:

```powershell
python -m pip install -r requirements.txt
```

## Uso

```powershell
python main.py
```

1. **Selecionar .PY** ou **Selecionar pasta** do projeto.
2. Confira o arquivo de entrada, o nome do EXE, o tipo (console/janela) e o ícone.
3. (Opcional) imports extras, arquivos adicionais e interpretador Python.
4. **GERAR EXECUTÁVEL**. O resultado aparece na pasta de saída (padrão: `<projeto>\dist`).

O builder **sugere** console ou janela conforme as bibliotecas importadas (ex.: `tkinter` → janela), mas a decisão é sua.

### Como o Python é escolhido (nesta ordem)

1. Interpretador informado no campo *Interpretador Python* (sem fallback se for inválido).
2. Ambiente virtual do projeto (`.venv`, `venv`, `env`).
3. O Python que está executando o builder (somente quando rodando pelo código-fonte).
4. `py -3`, `python`/`python3` no `PATH` e instalações padrão.

O `GUY Builder.exe` **nunca** é usado como interpretador.

### Linha de comando

```powershell
python main.py --cli --entry app\main.py --project app --name MeuApp --out dist --windowed --icon icone.ico
python main.py --cli -h
```

Opções: `--onedir`, `--hidden a,b`, `--add-data "origem|destino"`, `--python caminho\python.exe`, `--no-clean`, `--log-file`.
Código de saída: `0` sucesso, `1` erro de build, `2` cancelado.

## Self-build

```powershell
python main.py --cli --entry main.py --project . --name "GUY Builder" --windowed --icon assets\guymarck.ico --out dist
```

Gera `dist\GUY Builder.exe`. Esse executável usa um Python instalado para compilar outros projetos (também via `--cli`). Ele não consegue substituir a si mesmo enquanto está aberto: o builder recusa um destino igual ao `.exe` em execução.

## Arquitetura

```text
main.py                     ponto de entrada (GUI ou --cli)
guy_builder/
├── config.py               constantes, paleta, listas (configuração separada da lógica)
├── build_runner.py         pipeline de build (sem dependência de GUI)
├── python_finder.py        localização/validação do interpretador
├── dependencies.py         análise de imports e verificação no Python do build
├── cleaner.py              área temporária e publicação (limpeza restrita a artefatos do builder)
├── errors.py               erros estruturados (etapa/comando/solução) e classificação da saída
├── process_utils.py        subprocessos: ambiente limpo, sem janela, cancelamento
├── icon_tools.py           PNG → ICO        preview.py   pré-visualização
├── project.py  logger.py  settings.py  models.py  paths.py  cli.py
└── ui/                     theme.py, app.py, build_tab.py, icon_tab.py
assets/guymarck.ico         ícone do próprio builder
tests/                      test_core.py, test_ui_smoke.py, e2e_windows.py
```

## Limpeza e segurança

- Todo build roda em `%TEMP%\guybuilder_*` (com marcador próprio); nada é escrito na pasta do seu projeto.
- Na pasta de saída, só é substituído o artefato com o **mesmo nome** do executável. Uma pasta existente que não pareça saída do PyInstaller **não** é apagada.
- Pacotes ausentes nunca são instalados automaticamente (exceto o PyInstaller, com confirmação).

## Limitações

- Herda as limitações do PyInstaller (imports dinâmicos, DLLs, plugins, modelos, etc.). A detecção de imports é estática; imports por string/`importlib` não são vistos — use *Imports extras*.
- Os nomes de pacote PyPI exibidos como dica (`PIL → Pillow`...) são sugestões; confirme no PyPI.
- Um `.exe` do PyInstaller não é proteção de código; não embuta senhas/tokens.
- Windows é a plataforma alvo (o PyInstaller não faz cross-compile).
- Antivírus podem sinalizar executáveis gerados pelo PyInstaller (falso positivo comum).

## Testes

```powershell
python -m unittest discover -s tests -v     # núcleo + smoke da UI (PyInstaller simulado)
python tests\e2e_windows.py                 # teste REAL: Hello World, GUI, multi-arquivo e self-build
```

O `e2e_windows.py` executa o ciclo completo `código → GUY Builder.exe → outro.exe`, apaga o builder e confirma que o segundo executável roda sozinho.

## Licença

Ainda não definida. Adicione uma licença antes da distribuição pública.

---

<div align="center">

**GUY Builder** · Python → EXE → Windows

Construindo coisas desde as 3 da manhã. 🌙

</div>
