# Contexto do Projeto - Ponto Eletrônico

Este documento serve como a principal referência técnica e conceitual sobre a arquitetura, regras de negócio e infraestrutura do sistema de **Ponto Eletrônico**. Ele deve ser atualizado continuamente a cada nova funcionalidade implementada.

---

## 🛠️ Arquitetura e Ambiente de Desenvolvimento

- **Ambiente de Execução:** Windows (execução local ou em produção).
- **Linguagem Principal:** Python 3 (executado por meio de um ambiente virtual local `.venv`).
- **Framework Web:** Flask (com backend fornecendo APIs JSON e servindo arquivos estáticos/templates).
- **Banco de Dados (Dual-Mode / Híbrido):**
  - **Principal:** SQL Server 2022 (Instância `.\SQLEXPRESS`, banco de dados `PontoEletronicoDB`).
  - **Fallback/Local:** SQLite (`local.db`) utilizado de forma transparente quando o SQL Server está indisponível ou quando configurado explicitamente via variáveis de ambiente (`USE_SQLITE=true`).
- **Comunicação e Redes:**
  - Exposição externa para redes públicas por meio do **Ngrok** (com script automático para restaurar conexões e injetar authtoken do usuário).
  - Alternativa configurada para túneis via Cloudflare (`cloudflared`).
- **Portabilidade de Diretórios:** Todos os scripts `.bat` executam utilizando `%~dp0`. Isso garante que o projeto funcione a partir de qualquer diretório sem depender de caminhos estáticos ou absolutos rígidos.

---

## 💾 Modelagem de Dados (Banco de Dados)

### Principais Tabelas e Campos (SQL Server / SQLite)

1. **`Users` (Usuários do Sistema)**
   - `matricula` (NVARCHAR/TEXT, PK): Identificador único do funcionário.
   - `password` (NVARCHAR/TEXT): Hash bcrypt da senha de acesso.
   - `name` (NVARCHAR/TEXT): Nome completo do funcionário.
   - `cargo` (NVARCHAR/TEXT): Cargo ou função exercida.
   - `role` (NVARCHAR/TEXT): Permissões no sistema (`user` ou `admin`).
   - `must_change_password` (INT): Flag (0 ou 1) que obriga a troca de senha no primeiro login após um reset.
   - `carga_horaria` (INT): Carga horária semanal (ex: 25h, 30h, 40h).

2. **`TimeRecords` (Registros de Ponto)**
   - `id` (INT/INTEGER, PK): Identificador incremental.
   - `matricula` (NVARCHAR/TEXT): Matrícula associada ao ponto.
   - `date_str` (NVARCHAR/TEXT): Data do registro no formato `YYYY-MM-DD`.
   - `time1` até `time4` (NVARCHAR/TEXT): Horários de batidas diárias (Entrada 1, Saída 1, Entrada 2, Saída 2).
   - `obs_edocs` (NVARCHAR/TEXT): Observação oficial consolidada enviada para o sistema E-Docs (ex: "EXTERNO/DIÁRIA").
   - `justifications` (NVARCHAR/TEXT): Justificativas de correções inseridas administrativamente.
   - `is_retroactive` (INT): Flag indicando se alguma batida foi inserida retroativamente.

3. **`CustomHolidays` (Feriados Customizados)**
   - `date_str` (NVARCHAR/TEXT, PK): Data do feriado (`YYYY-MM-DD`).
   - `description` (NVARCHAR/TEXT): Nome ou descrição do feriado.

4. **`UserBalances` (Saldos Mensais de Horas)**
   - `matricula` (NVARCHAR/TEXT) & `year_month` (NVARCHAR/TEXT) (Composite Key/Unique): Controle acumulado de horas do funcionário para aquele mês.
   - `balance_seconds` (INT): Saldo do banco de horas convertido em segundos (positivo ou negativo).

---

## ⚙️ Regras de Operação e Boas Práticas

1. **Plataforma Windows Nativa:** Não sugerir ou introduzir contêineres Docker ou utilitários Linux para a execução do sistema local, a menos que solicitado expressamente.
2. **Caminhos de Arquivo:** Utilizar barras invertidas padrão do Windows (`\`) para caminhos locais e priorizar o uso de `%~dp0` nos scripts em lote.
3. **Padrão SQL:** Consultas e manipulações de banco de dados devem ser compatíveis tanto com o SQL Server (T-SQL) quanto com o SQLite, utilizando funções compatíveis ou adaptadores de driver (`pyodbc`, `pymssql` e `sqlite3`).
4. **Relatórios Excel:** A manipulação de planilhas Excel (geração do relatório de ponto oficial do SRE) é baseada na biblioteca `openpyxl`. Deve-se atentar ao preenchimento exato de células específicas e fórmulas matemáticas de soma/subtração de tempos de jornada.

---

## 🚀 Histórico Recente de Implementações

### 1. Desacoplamento de Observações e E-Docs
- A "Observação para E-Docs" (justificativas legais exibidas no PDF oficial) foi completamente separada das justificativas internas/administrativas de alteração de pontos. Isso evita a poluição do documento com notas internas.
- Ao excluir administrativamente uma batida de ponto, as observações associadas a ela são limpas automaticamente no banco para prevenir resquícios em relatórios futuros (registros fantasmas).

### 2. Registro Rápido Inteligente e Fuso Horário
- O fluxo de marcação de ponto rápido removeu a necessidade de selecionar datas redundantes. O sistema assume o fuso horário oficial local (`America/Sao_Paulo`).
- Ajustada a regra de detecção de batidas retroativas no período noturno para evitar falsos positivos de alterações fora de hora.

### 3. Gestão e Segurança de Acesso
- Criada a funcionalidade de **Reset de Senha** no Painel Administrativo. Quando acionado por um administrador, a senha do usuário retorna para o padrão `123456` e o flag `must_change_password` é ativado, obrigando o usuário a definir uma senha forte no próximo acesso.

### 4. Modalidade "Externo / Diária"
- Implementada uma modalidade para servidores em trabalho externo/viagens:
  - Preenche os 4 horários diários e consolida a observação "EXTERNO/DIÁRIA" de forma unificada no PDF do E-Docs.
  - No Excel gerado para o administrador, o saldo diário desse dia é fixado em `00:00:00`, impedindo o acúmulo indevido de créditos ou débitos no banco de horas.

### 5. Preenchimento Automático em Lote
- Adicionada funcionalidade para que o administrador realize a inserção automática das 4 batidas obrigatórias para um mês inteiro para um determinado usuário.
- O sistema pula automaticamente os fins de semana e dias em que já constam registros salvos, agilizando o fechamento de folhas de ponto.

### 6. Correção de Relatórios
- Corrigido o cálculo do **Saldo Anterior** (célula `Q4` do relatório Excel consolidado) tratando incompatibilidades de tipo e travamentos durante a leitura de saldos de meses passados.
- Retirados asteriscos de batidas retroativas quando não existirem justificativas reais anexadas à folha, limpando o visual do relatório.

### 7. Responsividade e Experiência do Usuário (UI/UX)
- Cabeçalho administrativo fixo com estilo blur translúcido (*glassmorphism*) preservando a identidade visual institucional (Brasão ES) sem colidir com os elementos da página.
- Adicionado um menu hambúrguer com barra lateral móvel retrátil (*drawer*) e rolagem independente para melhorar o uso do sistema em celulares e telas de baixa resolução (como datashows).

### 8. Carga Horária de 25 Horas Semanais
- Inclusão da opção de **25h** semanais nos cadastros.
- O motor de relatórios do backend distribui dinamicamente a jornada padrão de **5 horas diárias** para estes colaboradores ao exportar planilhas.

### 9. Automação e Inicialização do Sistema
- Scripts de automação simplificados e portáveis:
  - `INICIAR_SISTEMA.bat`: Executa o Flask e o túnel utilizando o Python do `.venv` local de forma transparente.
  - `SINCRONIZAR_DO_GITHUB.bat`, `ENVIAR_PARA_GITHUB.bat`: Agilizam a atualização do repositório remoto.
  - `GERAR_BACKUP_BANCO.bat`, `RESTAURAR_BANCO.bat`: Facilitam rotinas de cópia e recuperação do SQL Server local.
- Autenticação e reinicialização automáticas da rede de túneis configuradas no script `run_ngrok.py`.

---

## 📂 Estrutura do Workspace

- [app.py](file:///c:/got-rabalista/usr/PontoEletronico/app.py): Arquivo principal do servidor Flask com as APIs, controle de sessões e rotas de renderização.
- [CONTEXTO_PROJETO.md](file:///c:/got-rabalista/usr/PontoEletronico/CONTEXTO_PROJETO.md): Este arquivo de referência do projeto.
- [INICIAR_SISTEMA.bat](file:///c:/got-rabalista/usr/PontoEletronico/INICIAR_SISTEMA.bat): Inicializador do servidor web local.
- [GERAR_BACKUP_BANCO.bat](file:///c:/got-rabalista/usr/PontoEletronico/GERAR_BACKUP_BANCO.bat): Utilitário de backup do SQL Server.
- [RESTAURAR_BANCO.bat](file:///c:/got-rabalista/usr/PontoEletronico/RESTAURAR_BANCO.bat): Utilitário de restauração do banco de dados.
- [SINCRONIZAR_DO_GITHUB.bat](file:///c:/got-rabalista/usr/PontoEletronico/SINCRONIZAR_DO_GITHUB.bat): Atualização rápida do código via Git.
- `local.db`: Banco de dados SQLite local secundário.
- `templates/` & `static/`: Contêm as telas HTML, estilizações CSS e scripts JS que compõem o frontend.
 forma consistente em qualquer pasta em que o repositório estiver clonado (facilitando o funcionamento em múltiplas contas e caminhos locais).
