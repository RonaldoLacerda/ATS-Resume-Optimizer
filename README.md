# 📊 ATS Resume Optimizer  

**Aplicação web inteligente** que ajuda candidatos a otimizar currículos para sistemas de rastreamento de candidatos (ATS).  

## ✨ Funcionalidades Principais  

✅ **Upload de currículos**: Suporte para arquivos PDF e Word (DOC/DOCX)  
✅ **Análise ATS**: Calcula pontuação de compatibilidade com a vaga  
✅ **Identificação de keywords**: Detecta termos-chave faltantes no currículo  
✅ **Sugestões personalizadas**: Recomendações específicas para melhorar o currículo  
✅ **Banco de dados de vagas**: Armazena e recupera vagas de emprego  
✅ **Processamento de texto avançado**: Extração e análise de texto de documentos  

## 🛠️ Tecnologias Utilizadas  

| Backend            | Processamento        | Machine Learning     | Banco de Dados | Frontend          |
|--------------------|---------------------|----------------------|----------------|-------------------|
| Python 3 + Flask   | PyPDF2 + python-docx| scikit-learn         | MySQL          | HTML/CSS/JS + Jinja2 |

## 📋 Requisitos do Sistema  

- Python 3.8+  
- MySQL 5.7+  
- Bibliotecas Python (listadas em `requirements.txt`)  

## 🚀 Como Usar  

1. **Configure o ambiente**:  
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate    # Windows
   pip install -r requirements.txt
