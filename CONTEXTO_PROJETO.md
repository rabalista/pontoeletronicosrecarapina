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
