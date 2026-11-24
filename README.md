Reconhecimento facial para controle de acesso

Aplicação desktop em Python que simula o controle de acesso de uma catraca. Usa a câmera para detectar e reconhecer rostos, mantém usuários e registros de acesso em um banco SQLite e oferece telas de catraca, usuários e painel.

 Requisitos

- Python3
- Câmera conectada e disponível
- Dependências listadas em `requirements.txt`

 Instalação

Abra um terminal na pasta do projeto e crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente:

```powershell
 Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
 macOS ou Linux
source .venv/bin/activate
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

 Como executar

Na pasta principal do projeto, rode:

```bash
python main.py
```

Na primeira execução, o programa cria o banco `sistema_catraca.db` e inicializa o usuário administrador. Siga a tela de configuração para cadastrar os dados e as imagens faciais do administrador. Depois, use a tela de acesso à catraca para testar o reconhecimento. O banco é criado localmente quando o programa é iniciado.

 Estrutura do projeto

- `main.py`: inicializa o banco, prepara o serviço de reconhecimento e abre a interface.
- `access_control/`: interface gráfica, regras de acesso e persistência dos dados.
- `recognizer/`: detecção e reconhecimento facial.
- `recognizer/cascades/`: classificador Haar usado na detecção inicial de rostos.
- `requirements.txt`: dependências Python.

 Observações

O reconhecimento usa o modelo `buffalo_l` do InsightFace com execução em CPU. Na primeira inicialização, o InsightFace pode precisar baixar os arquivos do modelo. O sistema armazena os vetores faciais e o histórico de acesso no banco SQLite local.
