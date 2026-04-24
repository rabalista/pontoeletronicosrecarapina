# Instruções para Execução e Teste do Sistema

O sistema foi migrado para rodar no Windows com SQL Server.

## 1. Rodar Acesso Local (WiFi/Rede Interna)

Para iniciar o site no seu computador:

1. Abra o terminal (PowerShell ou CMD) na pasta `c:\usr\PontoEletronico`.
2. Execute o comando:

    ```bash
    python app.py
    ```

3. Abra o navegador e acesse: `http://localhost:5005`.

## 2. Rodar Acesso WEB (Internet / Celular)

Para que o sistema funcione na internet (Link do Cloudflare), use o script especial que preparamos:

1. Abra um **novo** terminal (não feche o anterior se estiver rodando, ou feche o anterior e abra este).
2. Execute:

    ```bash
    python run_cloudflare.py
    ```

3. Ele vai iniciar o sistema e tentar criar um "Túnel".
4. Fique de olho na tela. Quando aparecer **✨ TÚNEL PRONTO: https://...**, esse é o link que você deve usar no celular ou em outros computadores.

## 3. GitHub (Enviando o código)

1. Gere seu Token de Acesso Pessoal (Personal Access Token) no site do GitHub.
2. No terminal, digite:

    ```bash
    git push -u origin main
    ```

3. **Username**: `rabalista@edu.es.gov.br`
4. **Password**: Cole o **Token** que você gerou (não a senha do email).

## 4. Sobre o Banco de Dados

- Servidor: `SDUW0520228\SQLEXPRESS`
- Banco: `PontoEletronicoDB`
- Usuário: `admin_site`

Se tiver dúvidas ou erros, mande o erro aqui no chat!
