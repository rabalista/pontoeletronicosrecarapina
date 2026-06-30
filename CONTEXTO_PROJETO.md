# Contexto do Projeto - Ponto Eletrônico

## Ambiente de Desenvolvimento
- **Sistema Operacional:** Windows
- **Status:** Projeto recomeçado do zero (Docker descartado).
- **IDE:** Google Antigravity com extensão Graphify.

## Infraestrutura
- **Banco de Dados:** SQL Server 2022 (Instância Local).
- **Exposição Web:** Tunnel via ngrok.
- **Arquivos de Ponto:** Armazenados em pasta física local neste computador.
- **Versionamento:** GitHub (apenas código).

## Regras de Operação
1. Não sugerir comandos Docker ou Linux.
2. Usar caminhos de diretórios no formato Windows (ex: C:\...).
3. Scripts de banco de dados devem ser em T-SQL (SQL Server).

## Funcionalidades Implementadas (Histórico Recente)
- **Correção da Lógica de Observações no E-Docs:** Desacoplamento das justificativas de correções administrativas das observações inseridas pelos usuários. Garantia de que a "Observação para E-Docs" seja consistente em relatórios PDF e Excel.
- **Integridade de Dados e Exclusão Segura:** Rotinas de exclusão administrativa agora também apagam a observação original para evitar o vazamento de metadados em relatórios futuros (registros fantasmas).
- **Aprimoramento do Registro Rápido:** Remoção do campo de data redundante. Ajuste no fuso horário (`America/Sao_Paulo`) para não categorizar indevidamente batidas como "retroativas" à noite.
- **Redefinição de Senha de Usuários:** Nova ação para o administrador no painel de controle para "Resetar Senha", forçando o usuário a trocar a senha ao acessar a conta com a credencial padrão (`123456`).
- **Modalidade "Externo/Diária":** Implementação de uma nova modalidade de batida de ponto para dias de serviço externo que abrange os quatro tempos.
  - No PDF do E-Docs, a observação consolida como "EXTERNO/DIÁRIA" de maneira única por dia.
  - No Relatório Excel do Administrador, a coluna "Saldo Diário" daquele dia recebe o valor `00:00:00`, não gerando nem débito nem crédito para o banco de horas acumulado.
- **Preenchimento Automático em Lote:** Adicionada ferramenta para o administrador preencher as 4 batidas diárias de um mês inteiro de forma automática. O sistema ignora finais de semana e dias que já possuam ponto batido.
- **Correção da Geração de Relatórios (Excel/PDF):**
  - Ajuste na lógica do "Saldo Anterior" (Célula Q4 no Excel) para evitar erros de tipagem/travamentos na geração das planilhas.
  - Ocultamento de asteriscos indicativos de ajuste retroativo no E-Docs e outros relatórios quando a batida não contém justificativa real, evitando poluição visual em registros gerados automaticamente pelo sistema.
- **Aprimoramentos de Responsividade no Painel Administrativo:**
  - Cabeçalho fixo revitalizado com efeito glassmorphic blur (`backdrop-blur-md` e fundo branco semi-transparente) para manter o Brasão do Governo ES e título permanentemente fixados na tela de forma visualmente isolada e premium, sem overlaps.
  - Implementação de barra lateral (*drawer*) retrátil para dispositivos móveis acionada por menu hambúrguer, garantindo acesso completo a configurações de feriados e superintendentes no celular.
  - Habilitação de rolagem vertical independente (`overflow-y-auto`) na barra lateral para prevenir o encolhimento e embolamento de letras quando exibido em projetores/datashows de baixa resolução.
- **Nova Carga Horária (25h):**
  - Adicionada opção de carga horária de **25h** nas interfaces de cadastro inicial e gestão de usuários (administração).
  - O sistema de relatórios calcula e distribui de forma dinâmica as **5 horas diárias** nas planilhas Excel para os usuários com este modelo de carga horária.
- **Migração de Conta de Usuário no Windows e Automação do Ngrok:**
  - **Reconstrução do Ambiente Virtual (`.venv`):** Recriação do ambiente virtual do Python (`.venv`) nativo para Windows na pasta do projeto e de produção (`C:\usr\PontoEletronico`), resolvendo incompatibilidades de ambiente antigo e reinstalando todas as dependências (`flask`, `pymssql`, etc.) listadas em `requirements.txt`.
  - **Execução via `.venv`:** Ajuste no arquivo `INICIAR_SISTEMA.bat` para rodar os scripts utilizando o Python local do ambiente virtual (`.\.venv\Scripts\python.exe`), eliminando falhas de pacotes não encontrados no Python global do novo usuário.
  - **Autenticação Automática do Ngrok:** Implementação de rotina de autodetecção de configuração do Ngrok em `run_ngrok.py` para evitar solicitações redundantes de credenciais, incluindo o authtoken padrão do usuário diretamente no script como fallback seguro.
