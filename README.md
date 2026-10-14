# GUY Builder

> **Python → EXE. Simplificado.**

O **GUY Builder** é uma ferramenta gráfica para empacotamento de aplicações Python para Windows utilizando o [PyInstaller](https://pyinstaller.org/).

Em vez de configurar manualmente comandos de build, diretórios e opções do PyInstaller, o GUY Builder centraliza esse processo em uma interface gráfica simples, permitindo selecionar um projeto, identificar automaticamente seu ponto de entrada e gerar o executável com poucos passos.

---

## Overview

O objetivo do GUY Builder é tornar o processo de distribuição de aplicações Python mais simples e acessível, sem esconder o funcionamento do processo de empacotamento.

O Builder atua como uma camada gráfica sobre o PyInstaller, fornecendo:

- Detecção automática do entrypoint;
- Configuração visual do processo de build;
- Geração em `onefile` ou `onedir`;
- Execução em modo `windowed`;
- Suporte a ícones `.ico`;
- Configuração de `hidden-imports`;
- Limpeza de artefatos anteriores;
- Monitoramento do processo em tempo real;
- Cancelamento do build;
- Acesso rápido ao diretório de saída.

### Fluxo

```text
Projeto Python
      │
      ▼
┌─────────────────┐
│   GUY Builder   │
└────────┬────────┘
         │
         ├── Detecta entrypoint
         ├── Configura parâmetros
         ├── Executa PyInstaller
         └── Monitora o processo
                  │
                  ▼
              dist/
                  │
                  ▼
              Aplicação
                 .exe
```

---

## Features

### 📁 Project Discovery

Selecione a pasta raiz do projeto em vez de localizar manualmente o arquivo Python.

O GUY Builder percorre o projeto procurando possíveis pontos de entrada e ignora diretórios que normalmente não fazem parte do código-fonte da aplicação.

Diretórios ignorados incluem:

```text
.venv
venv
__pycache__
build
dist
.git
node_modules
```

---

### 🔎 Automatic Entrypoint Detection

O Builder prioriza arquivos com nomes convencionalmente utilizados como ponto de entrada:

```text
main.py
app.py
run.py
start.py
__main__.py
gui.py
```

Quando mais de uma possibilidade é encontrada, o usuário pode selecionar manualmente o arquivo desejado.

Isso permite trabalhar tanto com projetos simples quanto com estruturas maiores.

---

### 📦 Build Modes

O GUY Builder oferece os dois principais modos de distribuição do PyInstaller.

#### Onefile

Produz um único executável:

```text
dist/
└── MeuPrograma.exe
```

É o modo mais conveniente para distribuição.

#### Onedir

Produz um diretório contendo o executável e seus arquivos auxiliares:

```text
dist/
└── MeuPrograma/
    ├── MeuPrograma.exe
    ├── ...
    └── ...
```

Esse formato pode ser mais adequado para aplicações maiores ou projetos que dependem de diversos recursos externos.

---

### 🪟 Windowed Mode

Aplicações gráficas podem ser geradas utilizando o modo:

```text
--windowed
```

Isso impede a abertura de uma janela de console junto à aplicação.

Para aplicações CLI, o modo com console pode ser mantido.

---

### 🖼️ Application Icon

É possível definir um ícone `.ico` para o executável diretamente pela interface.

Exemplo:

```text
MeuPrograma.exe
      │
      └── ícone personalizado
```

O próprio GUY Builder também possui sua identidade visual incorporada ao código, evitando a dependência de um arquivo externo para renderizar sua interface.

---

### 🧠 Hidden Imports

Projetos que utilizam imports dinâmicos podem exigir módulos adicionais durante o processo de empacotamento.

O campo **Imports extras** permite informar esses módulos:

```text
numpy,pandas,meu_modulo
```

O Builder converte automaticamente a configuração para:

```text
--hidden-import numpy
--hidden-import pandas
--hidden-import meu_modulo
```

---

### 🧹 Build Cleanup

Antes de iniciar uma nova compilação, o Builder pode limpar artefatos gerados anteriormente, reduzindo a possibilidade de conflitos entre builds.

Entre os diretórios normalmente envolvidos estão:

```text
build/
dist/
```

A limpeza é realizada somente dentro do contexto do projeto selecionado.

---

### 📜 Real-time Build Log

A saída do PyInstaller é exibida diretamente na interface.

Isso permite acompanhar:

- Inicialização do processo;
- Análise dos módulos;
- Detecção de dependências;
- Warnings;
- Erros;
- Geração do executável;
- Finalização do build.

O log também facilita a identificação de problemas relacionados a dependências e imports.

---

### ⛔ Process Cancellation

Durante um build, o processo pode ser interrompido pela própria interface.

Isso evita a necessidade de finalizar manualmente o processo pelo terminal.

---

### 📂 Output Access

Após a conclusão do build, o Builder permite acessar rapidamente o diretório de saída.

Por padrão, os executáveis são disponibilizados dentro de:

```text
dist/
```

---

## Requirements

### Runtime

Para executar o GUY Builder a partir do código-fonte:

- Windows;
- Python 3.9 ou superior;
- Tkinter;
- Pip.

O PyInstaller pode ser instalado automaticamente pelo Builder quando não estiver disponível.

Também é possível instalar manualmente:

```powershell
python -m pip install pyinstaller
```

### Build Environment

O computador responsável por gerar o executável precisa possuir:

```text
Python
PyInstaller
```

O computador de destino **normalmente não precisa possuir Python instalado**.

Isso ocorre porque o PyInstaller empacota o interpretador Python e as dependências necessárias junto à aplicação.

---

## Installation

Clone o repositório:

```powershell
git clone <URL-DO-REPOSITORIO>
```

Entre no diretório:

```powershell
cd <PASTA-DO-REPOSITORIO>
```

Execute:

```powershell
python builder.py
```

Caso o PyInstaller não esteja instalado, instale-o com:

```powershell
python -m pip install pyinstaller
```

---

## Usage

### 1. Select Project

Abra o GUY Builder e selecione a pasta raiz do projeto Python.

### 2. Verify Entrypoint

O Builder realizará uma busca automática por arquivos Python candidatos.

Caso necessário, selecione manualmente o arquivo de entrada.

### 3. Configure Application

Defina:

- Nome do executável;
- Modo de distribuição;
- Execução com ou sem console;
- Ícone;
- Hidden imports.

### 4. Build

Clique em:

```text
⚡ GERAR EXE
```

O Builder iniciará o PyInstaller e exibirá o processo de compilação no log.

### 5. Access Output

Quando o processo terminar, o executável estará disponível no diretório:

```text
dist/
```

---

## Example

Considere o seguinte projeto:

```text
MeuProjeto/
├── main.py
├── modulo.py
├── assets/
│   ├── logo.png
│   └── config.json
└── requirements.txt
```

O GUY Builder pode identificar automaticamente:

```text
main.py
```

e gerar:

```text
MeuProjeto/
├── ...
├── build/
└── dist/
    └── MeuProjeto.exe
```

---

## Distributing Python Applications

O PyInstaller não transforma Python em um binário nativo independente da linguagem.

Ele cria um pacote contendo o interpretador Python, o código da aplicação e as dependências necessárias para execução.

Portanto, existe uma diferença importante entre o ambiente de **build** e o ambiente de **execução**:

| Ambiente | Python necessário |
|---|---|
| Máquina que gera o EXE | Sim |
| Máquina que executa o EXE | Normalmente não |

Entretanto, a portabilidade depende das características da aplicação e de suas dependências.

Projetos que utilizam componentes nativos, DLLs, recursos externos ou mecanismos de importação dinâmica podem exigir configuração adicional.

---

## External Resources

O PyInstaller não identifica necessariamente todos os arquivos utilizados indiretamente pela aplicação.

Dependendo do projeto, pode ser necessário incluir manualmente:

```text
Imagens
JSON
YAML
Modelos
DLLs
Bancos de dados
Arquivos de configuração
Executáveis externos
```

Nesses casos, podem ser necessárias opções adicionais do PyInstaller, como:

```text
--add-data
--add-binary
--hidden-import
```

ou uma configuração `.spec`.

O GUY Builder simplifica os casos comuns, mas não substitui as possibilidades avançadas do PyInstaller.

---

## Important: File Paths

Aplicações empacotadas devem evitar depender de caminhos absolutos específicos da máquina de desenvolvimento.

Evite estruturas como:

```python
C:\Users\Joao\Documents\MeuProjeto\arquivo.json
```

Prefira caminhos relativos à aplicação ou mecanismos apropriados de resolução de recursos.

Isso é especialmente importante quando o executável será distribuído para outros computadores.

---

## Security

O empacotamento de uma aplicação Python **não é um mecanismo de proteção ou criptografia de código**.

O PyInstaller facilita a distribuição, mas não impede engenharia reversa do executável.

Não armazene diretamente no código distribuído:

```text
API Keys
Tokens
Senhas
Credenciais
Chaves privadas
Segredos de produção
```

Quando informações sensíveis forem necessárias, utilize mecanismos apropriados de gerenciamento de segredos e autenticação.

---

## Building GUY Builder

O próprio GUY Builder pode ser empacotado utilizando o PyInstaller.

Com o PyInstaller instalado:

```powershell
python -m PyInstaller --onefile --windowed --name "GUY Builder" builder.py
```

O executável será criado em:

```text
dist/
└── GUY Builder.exe
```

Como os elementos visuais necessários à interface estão incorporados ao projeto, o executável não depende de um arquivo separado para exibir a identidade visual do Builder.

---

## Project Structure

Uma estrutura recomendada para o projeto é:

```text
GUY-Builder/
├── builder.py
├── README.md
├── requirements.txt
├── build/
└── dist/
```

Projetos empacotados pelo Builder podem possuir qualquer estrutura compatível com o PyInstaller.

---

## Limitations

O GUY Builder é uma interface gráfica para o PyInstaller e, portanto, herda suas limitações.

Dependendo da aplicação, podem ser necessárias configurações adicionais para:

- Imports dinâmicos;
- Bibliotecas nativas;
- DLLs;
- Arquivos externos;
- Modelos de IA;
- Bancos de dados;
- Recursos gráficos;
- Executáveis auxiliares;
- Plugins;
- Sistemas de carregamento dinâmico.

Para casos mais complexos, a configuração `.spec` do PyInstaller continua sendo a alternativa mais completa.

Também é recomendado gerar o executável em um ambiente compatível com o sistema operacional e a arquitetura de destino.

---

## Why GUY Builder?

O objetivo do projeto não é substituir o PyInstaller.

É **reduzir a complexidade operacional que existe ao redor dele**.

O fluxo tradicional pode exigir:

```text
Terminal
   ↓
Localizar projeto
   ↓
Encontrar entrypoint
   ↓
Configurar parâmetros
   ↓
Executar PyInstaller
   ↓
Interpretar logs
   ↓
Verificar saída
```

Com o GUY Builder:

```text
Selecionar projeto
        ↓
Configurar
        ↓
GERAR EXE
        ↓
Aplicação pronta
```

A ferramenta transforma um processo predominantemente baseado em linha de comando em uma experiência gráfica orientada ao projeto.

---

## Technology Stack

| Tecnologia | Função |
|---|---|
| Python | Linguagem principal |
| Tkinter | Interface gráfica |
| PyInstaller | Empacotamento da aplicação |
| pathlib | Manipulação de caminhos |
| subprocess | Execução do processo de build |
| Windows | Plataforma alvo |

---

## Roadmap

Possíveis evoluções do projeto:

- [ ] Suporte a múltiplos entrypoints avançados;
- [ ] Configuração de `--add-data`;
- [ ] Configuração de `--add-binary`;
- [ ] Suporte visual a arquivos `.spec`;
- [ ] Presets de build;
- [ ] Histórico de builds;
- [ ] Detecção de dependências;
- [ ] Validação automática do projeto;
- [ ] Exportação/importação de configurações;
- [ ] Temas visuais;
- [ ] Empacotamento de projetos mais complexos;
- [ ] Sistema de diagnóstico de erros do PyInstaller.

---

## License

Este projeto ainda não possui uma licença definida.

Uma licença deverá ser adicionada antes da distribuição pública do projeto.

---

<div align="center">

### GUY Builder

**Python → EXE → Windows**

Construindo coisas desde as 3 da manhã. 🌙

</div>