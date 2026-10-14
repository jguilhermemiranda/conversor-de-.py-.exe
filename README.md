# GUY Builder

> **Python → EXE, sem complicação.**

O **GUY Builder** é uma interface gráfica para transformar projetos Python em executáveis Windows usando **PyInstaller**.

A ideia é simplificar o fluxo: em vez de procurar manualmente um arquivo `.py`, você seleciona a **pasta do projeto**, e o Builder procura automaticamente um possível ponto de entrada.

## ✨ Principais recursos

- 📁 Seleção da pasta inteira do projeto.
- 🔎 Detecção automática do arquivo de entrada (`main.py`, `app.py`, `run.py`, `start.py`, `__main__.py` e outros).
- 🧩 Escolha manual do entrypoint quando houver mais de uma possibilidade.
- 📦 Geração em `--onefile` ou `--onedir`.
- 🪟 Opção de executar sem console com `--windowed`.
- 🧹 Limpeza automática dos artefatos de build.
- 🖼️ Suporte a ícone `.ico`.
- 🧠 Campo para `--hidden-import`, útil em projetos com imports dinâmicos.
- 📜 Log em tempo real.
- ⛔ Cancelamento do processo.
- 📂 Abertura rápida da pasta de saída.
- 🎨 Interface inspirada na identidade visual da marca GUY.
- 🚫 O `.exe` gerado pelo PyInstaller não precisa que o usuário final tenha Python instalado.

## ⚠️ O que significa "não precisar instalar Python"?

O executável gerado pelo PyInstaller inclui o interpretador Python e os módulos necessários detectados durante o processo de build.

Portanto:

**Computador que gera o EXE:** precisa ter Python + PyInstaller.

**Computador que recebe o EXE:** normalmente não precisa instalar Python.

Isso não significa que qualquer projeto Python automaticamente será portátil. Bibliotecas com componentes nativos, arquivos externos, imports dinâmicos, DLLs ou recursos adicionais podem exigir configuração extra.

## 🖥️ Requisitos

Para executar o Builder a partir do código-fonte:

- Windows
- Python 3.9+
- Tkinter
- Pip

O PyInstaller pode ser instalado automaticamente pelo próprio Builder caso não esteja disponível.

Para garantir uma instalação manual:

```powershell
python -m pip install pyinstaller
```

## 🚀 Como usar

### 1. Execute o Builder

```powershell
python builder.py
```

### 2. Selecione a pasta do projeto

Clique em:

**Selecionar pasta**

O Builder irá procurar arquivos `.py` dentro dela.

Pastas comuns de ambiente e artefatos, como:

- `.venv`
- `venv`
- `__pycache__`
- `build`
- `dist`
- `.git`
- `node_modules`

são ignoradas na busca do entrypoint.

### 3. Confira o arquivo de entrada

O Builder prioriza nomes convencionais:

```text
main.py
app.py
run.py
start.py
__main__.py
gui.py
```

Se houver várias opções, você pode escolher manualmente no campo **Arquivo de entrada**.

### 4. Configure o nome

Informe o nome que o `.exe` deverá receber.

Exemplo:

```text
MeuPrograma
```

Resultado:

```text
MeuPrograma.exe
```

### 5. Gere o executável

Clique em:

**⚡ GERAR EXE**

O processo será executado pelo PyInstaller e o log será exibido na própria interface.

## 📦 Onefile x Onedir

### Onefile

Gera:

```text
MeuPrograma.exe
```

É a opção mais prática para distribuir um programa.

### Onedir

Gera uma pasta contendo o executável e seus arquivos auxiliares.

É interessante quando o programa possui muitos recursos ou quando você quer analisar os arquivos gerados pelo PyInstaller.

## 🧠 Imports dinâmicos

Algumas bibliotecas utilizam imports que o PyInstaller pode não conseguir detectar automaticamente.

Nesse caso, utilize o campo:

**Imports extras**

Exemplo:

```text
numpy,pandas,meu_modulo
```

O Builder transforma isso em:

```text
--hidden-import numpy
--hidden-import pandas
--hidden-import meu_modulo
```

## 🖼️ Ícone

O Builder aceita arquivos:

```text
.ico
```

Selecione o ícone no campo **Ícone .ico**.

A imagem da marca GUY utilizada na interface é incorporada ao próprio `builder.py`, então a interface não depende de um arquivo externo para exibir a marca.

## 📁 Estrutura recomendada

Um projeto simples pode ser:

```text
MeuProjeto/
├── main.py
├── modulo.py
├── assets/
│   └── ...
└── requirements.txt
```

Depois:

```text
GUY Builder
   ↓
Selecionar pasta
   ↓
Detectar main.py
   ↓
Gerar EXE
   ↓
dist/
   └── MeuProjeto.exe
```

## 🔧 Gerando o próprio GUY Builder como EXE

Depois de instalar o PyInstaller:

```powershell
python -m PyInstaller --onefile --windowed --name "GUY Builder" builder.py
```

O executável aparecerá em:

```text
dist/GUY Builder.exe
```

Como o logo está embutido no código, ele acompanha o executável.

## 🧪 Desenvolvimento

Clone o projeto e execute:

```powershell
git clone <URL-DO-REPOSITORIO>
cd <PASTA-DO-REPOSITORIO>
python builder.py
```

## 🛠️ Limitações

O GUY Builder é uma interface para o PyInstaller; ele não substitui o mecanismo de empacotamento.

Se o projeto utilizar:

- imports dinâmicos;
- DLLs externas;
- arquivos JSON/YAML;
- imagens;
- modelos de IA;
- bancos de dados;
- executáveis externos;
- arquivos acessados por caminhos absolutos;

pode ser necessário configurar `--hidden-import`, `--add-data`, DLLs ou um arquivo `.spec`.

Também é importante gerar o executável no mesmo sistema operacional/arquitetura de destino quando houver dependências nativas específicas.

## 🔐 Segurança

Um `.exe` empacotado não é uma forma de criptografar o código Python.

PyInstaller empacota o programa; ele não transforma Python em código nativo impossível de analisar.

Não coloque:

- senhas;
- tokens;
- chaves privadas;
- API keys;
- credenciais;

diretamente no código de um aplicativo distribuído.

## 📄 Licença

Defina aqui a licença escolhida para o projeto antes de publicar o repositório.

---

## GUY

**GUY Builder — construindo coisas desde as 3 da manhã.**

Python → EXE → Windows.

Feito para deixar o processo de distribuição de aplicações Python mais simples.
