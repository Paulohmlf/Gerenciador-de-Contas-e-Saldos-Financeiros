# 💰 Gerenciador de Contas e Saldos Financeiros

Um aplicativo web simples e direto, desenvolvido em **Python (Flask)**, para organizar contas financeiras e controlar saldos.  
Ideal para quem precisa registrar movimentações de forma prática, com suporte a múltiplas contas, paginação e formatação em **padrão brasileiro (R$ 1.234,56)**.  

---

## ✨ Funcionalidades

- 📌 **Criação de contas** com código único e descrição personalizada.  
- 💵 **Registro de saldos** com valor, descrição opcional e data/hora automática.  
- 📊 **Visualização paginada** de todos os registros, em ordem cronológica.  
- 🔍 **Detalhes por conta**, com histórico específico.  
- ✅ **Validações** para valores monetários e descrições.  
- ⚠️ **Tratamento de erros** com páginas customizadas (404 e 500).  
- ⚙️ **Configurações flexíveis** para desenvolvimento e produção, via variáveis de ambiente.  

---

## 🛠️ Tecnologias

- **Backend**: [Flask](https://flask.palletsprojects.com/)  
- **Banco de Dados**: [SQLAlchemy](https://www.sqlalchemy.org/) com SQLite (fácil migração para PostgreSQL, MySQL etc.)  
- **Templates**: [Jinja2](https://jinja.palletsprojects.com/) + HTML/CSS (com suporte a Bootstrap)  
- **Outros**: `decimal.Decimal` para precisão financeira, logging configurado para depuração.  

---

## 🚀 Como Rodar Localmente

1. **Clone o repositório**  
   ```bash
   git clone https://github.com/Paulohmlf/Gerenciador-de-Contas-e-Saldos-Financeiros.git
   cd Gerenciador-de-Contas-e-Saldos-Financeiros
   ```

2. **Crie e ative um ambiente virtual (opcional, mas recomendado)**  
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. **Instale as dependências**  
   ```bash
   pip install flask flask-sqlalchemy
   ```

4. **Configure variáveis de ambiente (opcional)**  
   ```bash
   export FLASK_ENV=development   # ou production
   export SECRET_KEY="sua_chave_secreta"
   export DATABASE_URL="sqlite:///Formulario.db"
   ```

5. **Execute o servidor**  
   ```bash
   python app.py
   ```
   Acesse: [http://localhost:5000](http://localhost:5000)  

---

## 📂 Estrutura do Projeto

```
📦 Gerenciador-de-Contas-e-Saldos-Financeiros
 ┣ 📜 app.py                # Código principal (rotas, modelos e lógica)
 ┣ 📂 templates/            # Arquivos HTML (Jinja2)
 ┃ ┣ base.html              # Layout base
 ┃ ┣ form.html              # Formulário para novos registros
 ┃ ┣ index.html             # Página inicial com tabela paginada
 ┃ ┣ account_detail.html    # Detalhes de uma conta
 ┃ ┣ 404.html               # Página de erro 404
 ┃ ┗ 500.html               # Página de erro 500
 ┣ 📂 static/               # (opcional) CSS/JS se houver
 ┗ 📜 README.md             # Documentação do projeto
```

---

## 📖 Exemplos de Uso

1. Crie ou selecione uma conta.  
2. Registre um saldo, ex.: **"R$ 1.234,56 – Salário"**.  
3. Visualize o histórico na página inicial ou nos detalhes da conta.  

---

## 📌 Notas Importantes

- Utiliza **chaves compostas** no modelo `Saldo` para evitar IDs sequenciais simples.  
- Formatação de valores segue o **padrão brasileiro**.  
- Para produção, configure uma `SECRET_KEY` segura e use um banco robusto (PostgreSQL, MySQL etc.).  
- Atualmente focado em CRUD de contas e saldos. Futuramente pode receber:
  - 📑 Relatórios de entradas/saídas  
  - 🔐 Autenticação de usuários  
  - 📈 Gráficos e dashboards  

---

## 🤝 Contribuições

Sinta-se à vontade para abrir **issues** ou enviar **pull requests**.  
Sugestões de melhorias são sempre bem-vindas!  

---

## 📝 Licença

Este projeto é distribuído sob a licença MIT.  
Você pode usar, modificar e distribuir livremente.  
