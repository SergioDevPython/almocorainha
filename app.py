import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, date
from fpdf import FPDF

# Configuração da página
st.set_page_config(
    page_title="ESCOLA MUNICIPAL RAINHA DA PAZ",
    page_icon="🏫",
    layout="wide"
)

# Classe para geração do PDF com cabeçalho e rodapé personalizados
class PDFRelatorio(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 8, 'ESCOLA MUNICIPAL RAINHA DA PAZ', align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('Helvetica', 'I', 11)
        self.cell(0, 6, 'Relatorio Semanal de Alimentacao Escolar', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 9)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, 'Desenvolvido por Sergio Santos', align='C')

def gerar_pdf_bytes(df_relatorio, turma, data_inicio_str, data_fim_str):
    pdf = PDFRelatorio(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # Informações da Turma e Período
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, f"Turma: {turma}  |  Periodo: {data_inicio_str} a {data_fim_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    # Tabela - Cabeçalho
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(230, 230, 230)
    
    col_widths = [75, 25, 25, 28, 35]  # Soma = 188mm (cabe bem na A4)
    headers = ["Aluno", "Dias Reg.", "Almocou", "Nao Almocou", "% Presenca"]
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align='C', fill=True)
    pdf.ln()
    
    # Tabela - Dados
    pdf.set_font('Helvetica', '', 9)
    for _, row in df_relatorio.iterrows():
        # Remove caracteres especiais/acentos para compatibilidade com FPDF padrão
        nome_aluno = row["Aluno"].encode('latin-1', 'replace').decode('latin-1')
        
        pdf.cell(col_widths[0], 7, nome_aluno, border=1)
        pdf.cell(col_widths[1], 7, str(row["Dias Registrados"]), border=1, align='C')
        pdf.cell(col_widths[2], 7, str(row["Almoçou (Dias)"]), border=1, align='C')
        pdf.cell(col_widths[3], 7, str(row["Não Almoçou (Dias)"]), border=1, align='C')
        pdf.cell(col_widths[4], 7, str(row["% Presença no Almoço"]), border=1, align='C')
        pdf.ln()
        
    return bytes(pdf.output())


# Conexão com MongoDB Atlas
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["MONGO_URI"])

client = init_connection()
db = client["controle_almoco"]
collection_alunos = db["alunos"]
collection_frequencia = db["frequencia"]

# Título Principal
st.title("🏫 ESCOLA MUNICIPAL RAINHA DA PAZ")
st.subheader("Sistema de Controle de Alimentação Escolar")
st.markdown("---")

# Gerar lista de turmas (1º A ao 5º C)
turmas_disponiveis = []
for ano in range(1, 6):
    for turma in ['A', 'B', 'C']:
        turmas_disponiveis.append(f"{ano}º {turma}")

# Navegação Lateral
menu = st.sidebar.radio(
    "Navegação",
    ["📋 Registro Diário (Almoço)", "➕ Cadastrar Alunos", "📊 Relatórios e Impressão"]
)

# -------------------------------------------------------------------
# ABA 1: CADASTRAR ALUNOS
# -------------------------------------------------------------------
if menu == "➕ Cadastrar Alunos":
    st.header("Cadastrar Novo Aluno")
    
    with st.form("form_cadastro"):
        nome_aluno = st.text_input("Nome do Aluno:")
        turma_aluno = st.selectbox("Turma:", turmas_disponiveis)
        submitted = st.form_submit_button("Salvar Aluno")
        
        if submitted:
            if nome_aluno.strip() != "":
                collection_alunos.insert_one({
                    "nome": nome_aluno.strip(),
                    "turma": turma_aluno
                })
                st.success(f"Aluno {nome_aluno} cadastrado na turma {turma_aluno} com sucesso!")
            else:
                st.warning("Por favor, digite o nome do aluno.")

    st.markdown("---")
    st.subheader("Alunos Cadastrados")
    turma_filtro = st.selectbox("Filtrar por Turma para visualizar:", turmas_disponiveis)
    alunos_turma = list(collection_alunos.find({"turma": turma_filtro}))
    
    if alunos_turma:
        df_alunos = pd.DataFrame(alunos_turma)
        st.dataframe(df_alunos[["nome", "turma"]], use_container_width=True)
    else:
        st.info("Nenhum aluno cadastrado nesta turma.")

# -------------------------------------------------------------------
# ABA 2: REGISTRO DIÁRIO DE ALMOÇO (CHECKLIST)
# -------------------------------------------------------------------
elif menu == "📋 Registro Diário (Almoço)":
    st.header("Registro Diário de Alimentação")
    
    col1, col2 = st.columns(2)
    with col1:
        turma_sel = st.selectbox("Selecione a Turma:", turmas_disponiveis)
    with col2:
        data_sel = st.date_input("Data do Registro:", date.today())
        data_str = data_sel.strftime("%Y-%m-%d")

    alunos = list(collection_alunos.find({"turma": turma_sel}).sort("nome", 1))
    
    if not alunos:
        st.warning("Nenhum aluno cadastrado nesta turma.")
    else:
        st.write("Marque a caixa dos alunos que **NÃO ALMOÇARAM** hoje na escola:")
        
        # Buscar registros do dia para pré-preencher
        registro_existente = collection_frequencia.find_one({
            "turma": turma_sel,
            "data": data_str
        })
        
        nao_almocaram_salvos = registro_existente["nao_almocaram"] if registro_existente else []
        
        nao_almocaram_atuais = []
        
        with st.form("form_almoco"):
            for aluno in alunos:
                id_str = str(aluno["_id"])
                ja_marcado = id_str in nao_almocaram_salvos
                
                marcado = st.checkbox(
                    f"{aluno['nome']}", 
                    value=ja_marcado,
                    key=id_str
                )
                if marcado:
                    nao_almocaram_atuais.append(id_str)
            
            salvar = st.form_submit_button("Salvar Frequência de Almoço")
            
            if salvar:
                collection_frequencia.update_one(
                    {"turma": turma_sel, "data": data_str},
                    {"$set": {
                        "turma": turma_sel,
                        "data": data_str,
                        "nao_almocaram": nao_almocaram_atuais
                    }},
                    upsert=True
                )
                st.success("Registro de almoço salvo com sucesso!")

# -------------------------------------------------------------------
# ABA 3: RELATÓRIOS, PORCENTAGEM E IMPRESSÃO
# -------------------------------------------------------------------
elif menu == "📊 Relatórios e Impressão":
    st.header("Relatório Semanal / Consulta de Almoço")
    
    turma_rel = st.selectbox("Selecione a Turma:", turmas_disponiveis)
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        data_inicio = st.date_input("Data Inicial:", date.today() - pd.Timedelta(days=7))
    with col_d2:
        data_fim = st.date_input("Data Final:", date.today())
        
    if st.button("Gerar Relatório"):
        str_inicio = data_inicio.strftime("%Y-%m-%d")
        str_fim = data_fim.strftime("%Y-%m-%d")
        
        # Buscar dias registrados no período
        registros = list(collection_frequencia.find({
            "turma": turma_rel,
            "data": {"$gte": str_inicio, "$lte": str_fim}
        }))
        
        alunos = list(collection_alunos.find({"turma": turma_rel}).sort("nome", 1))
        
        total_dias = len(registros)
        
        if total_dias == 0:
            st.warning("Nenhum registro encontrado no período selecionado.")
        else:
            relatorio_data = []
            
            for aluno in alunos:
                id_str = str(aluno["_id"])
                dias_almocou = 0
                dias_nao_almocou = 0
                
                for r in registros:
                    if id_str in r.get("nao_almocaram", []):
                        dias_nao_almocou += 1
                    else:
                        dias_almocou += 1
                
                pct_almocou = (dias_almocou / total_dias) * 100
                
                relatorio_data.append({
                    "Aluno": aluno["nome"],
                    "Dias Registrados": total_dias,
                    "Almoçou (Dias)": dias_almocou,
                    "Não Almoçou (Dias)": dias_nao_almocou,
                    "% Presença no Almoço": f"{pct_almocou:.1f}%"
                })
            
            df_relatorio = pd.DataFrame(relatorio_data)
            
            st.subheader(f"Relatório da Turma {turma_rel} ({data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')})")
            st.dataframe(df_relatorio, use_container_width=True)
            
            st.markdown("### 🖨️ Opções de Download / Impressão")
            col_down1, col_down2 = st.columns(2)
            
            # Botão 1: PDF
            with col_down1:
                pdf_bytes = gerar_pdf_bytes(
                    df_relatorio, 
                    turma_rel, 
                    data_inicio.strftime('%d/%m/%Y'), 
                    data_fim.strftime('%d/%m/%Y')
                )
                st.download_button(
                    label="📄 Baixar Relatório em PDF",
                    data=pdf_bytes,
                    file_name=f"relatorio_almoco_{turma_rel}_{str_inicio}.pdf",
                    mime="application/pdf"
                )
            
            # Botão 2: CSV (Excel)
            with col_down2:
                csv = df_relatorio.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📊 Baixar Planilha (CSV)",
                    data=csv,
                    file_name=f"relatorio_almoco_{turma_rel}_{str_inicio}.csv",
                    mime="text/csv"
                )

# -------------------------------------------------------------------
# RODAPÉ
# -------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Desenvolvido por Sergio Santos"
    "</div>",
    unsafe_allow_html=True
)