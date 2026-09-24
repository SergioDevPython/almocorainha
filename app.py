import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, date
from fpdf import FPDF

# -------------------------------------------------------------------
# CONFIGURAÇÃO E CSS MOBILE FIRST
# -------------------------------------------------------------------
st.set_page_config(
    page_title="ESCOLA MUNICIPAL RAINHA DA PAZ",
    page_icon="🏫",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilização CSS para transformar em interface de aplicativo mobile
st.markdown("""
<style>
    /* Estilização geral para telas menores */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Botões grandes e fáceis de tocar com o polegar */
    div.stButton > button {
        width: 100% !important;
        height: 60px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        margin-bottom: 8px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.08) !important;
    }
    
    /* Aumenta áreas de clique das caixas de seleção (Checkboxes) no celular */
    .stCheckbox {
        background-color: #ffffff;
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin-bottom: 8px;
    }
    
    .stCheckbox label p {
        font-size: 18px !important;
        font-weight: 500 !important;
        color: #212529 !important;
    }
    
    /* Melhoria visual para formulários e seletores */
    .stSelectbox label, .stTextInput label, .stDateInput label {
        font-size: 16px !important;
        font-weight: bold !important;
        color: #343a40 !important;
    }

    /* Cartões de métrica */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# CLASSE GERADORA DE PDF
# -------------------------------------------------------------------
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

def gerar_pdf_bytes(df_relatorio, turma, data_inicio_str, data_fim_str, total_nao_almocaram):
    pdf = PDFRelatorio(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, f"Turma: {turma}  |  Periodo: {data_inicio_str} a {data_fim_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Total de refeicoes NAO realizadas na turma: {total_nao_almocaram}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(230, 230, 230)
    
    col_widths = [75, 25, 25, 28, 35]
    headers = ["Aluno", "Dias Reg.", "Almocou", "Nao Almocou", "% Presenca"]
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font('Helvetica', '', 9)
    for _, row in df_relatorio.iterrows():
        nome_aluno = str(row["Aluno"]).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(col_widths[0], 7, nome_aluno, border=1)
        pdf.cell(col_widths[1], 7, str(row["Dias Registrados"]), border=1, align='C')
        pdf.cell(col_widths[2], 7, str(row["Almoçou (Dias)"]), border=1, align='C')
        pdf.cell(col_widths[3], 7, str(row["Não Almoçou (Dias)"]), border=1, align='C')
        pdf.cell(col_widths[4], 7, str(row["% Presença no Almoço"]), border=1, align='C')
        pdf.ln()
        
    return bytes(pdf.output())

# -------------------------------------------------------------------
# BANCO DE DADOS E ESTADO DA SESSÃO
# -------------------------------------------------------------------
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["MONGO_URI"])

client = init_connection()
db = client["controle_almoco"]
collection_alunos = db["alunos"]
collection_frequencia = db["frequencia"]

# Estado inicial da tela do menu principal
if "tela" not in st.session_state:
    st.session_state.tela = "home"

# Lista de turmas do 1º A ao 5º C
turmas_disponiveis = [f"{ano}º {turma}" for ano in range(1, 6) for turma in ['A', 'B', 'C']]

# -------------------------------------------------------------------
# CABEÇALHO DO APP
# -------------------------------------------------------------------
st.markdown("<h2 style='text-align: center; color: #1E3A8A; margin-bottom: 0;'>🏫 ESCOLA MUNICIPAL RAINHA DA PAZ</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6B7280; margin-top: 0;'>Controle de Alimentação Escolar</p>", unsafe_allow_html=True)
st.markdown("---")

# -------------------------------------------------------------------
# TELA INICIAL (MENU COM BOTÕES GRANDES)
# -------------------------------------------------------------------
if st.session_state.tela == "home":
    st.subheader("Selecione uma opção:")
    
    if st.button("📋 REGISTRO DIÁRIO DE ALMOÇO", type="primary"):
        st.session_state.tela = "registro"
        st.rerun()
        
    if st.button("➕ CADASTRAR ALUNOS"):
        st.session_state.tela = "cadastro"
        st.rerun()
        
    if st.button("📊 RELATÓRIOS E IMPRESSÃO"):
        st.session_state.tela = "relatorios"
        st.rerun()

# -------------------------------------------------------------------
# TELA 1: REGISTRO DIÁRIO DE ALMOÇO (CHECKLIST)
# -------------------------------------------------------------------
elif st.session_state.tela == "registro":
    if st.button("⬅️ Voltar ao Menu"):
        st.session_state.tela = "home"
        st.rerun()
        
    st.header("📋 Registro Diário")
    
    turma_sel = st.selectbox("Selecione a Turma:", turmas_disponiveis)
    data_sel = st.date_input("Data do Registro:", date.today())
    data_str = data_sel.strftime("%Y-%m-%d")

    alunos = list(collection_alunos.find({"turma": turma_sel}).sort("nome", 1))
    
    if not alunos:
        st.warning("Nenhum aluno cadastrado nesta turma.")
    else:
        st.info("Marque APENAS os alunos que **NÃO ALMOÇARAM** hoje:")
        
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
            
            salvar = st.form_submit_button("💾 SALVAR FREQUÊNCIA", type="primary")
            
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
                st.success("✅ Registro de almoço salvo com sucesso!")

# -------------------------------------------------------------------
# TELA 2: CADASTRAR ALUNOS
# -------------------------------------------------------------------
elif st.session_state.tela == "cadastro":
    if st.button("⬅️ Voltar ao Menu"):
        st.session_state.tela = "home"
        st.rerun()
        
    st.header("➕ Cadastrar Aluno")
    
    with st.form("form_cadastro"):
        nome_aluno = st.text_input("Nome do Aluno:")
        turma_aluno = st.selectbox("Turma:", turmas_disponiveis)
        submitted = st.form_submit_button("💾 CADASTRAR ALUNO", type="primary")
        
        if submitted:
            if nome_aluno.strip() != "":
                collection_alunos.insert_one({
                    "nome": nome_aluno.strip(),
                    "turma": turma_aluno
                })
                st.success(f"✅ {nome_aluno} cadastrado na turma {turma_aluno}!")
            else:
                st.warning("Por favor, digite o nome do aluno.")

    st.markdown("---")
    st.subheader("Alunos Cadastrados")
    turma_filtro = st.selectbox("Filtrar Turma:", turmas_disponiveis)
    alunos_turma = list(collection_alunos.find({"turma": turma_filtro}))
    
    if alunos_turma:
        df_alunos = pd.DataFrame(alunos_turma)
        st.dataframe(df_alunos[["nome", "turma"]], use_container_width=True)
    else:
        st.info("Nenhum aluno cadastrado nesta turma.")

# -------------------------------------------------------------------
# TELA 3: RELATÓRIOS E IMPRESSÃO PDF
# -------------------------------------------------------------------
elif st.session_state.tela == "relatorios":
    if st.button("⬅️ Voltar ao Menu"):
        st.session_state.tela = "home"
        st.rerun()
        
    st.header("📊 Relatório Semanal")
    
    turma_rel = st.selectbox("Selecione a Turma:", turmas_disponiveis)
    data_inicio = st.date_input("Data Inicial:", date.today() - pd.Timedelta(days=7))
    data_fim = st.date_input("Data Final:", date.today())
        
    if st.button("🔍 GERAR RELATÓRIO", type="primary"):
        str_inicio = data_inicio.strftime("%Y-%m-%d")
        str_fim = data_fim.strftime("%Y-%m-%d")
        
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
            soma_nao_almocaram_turma = 0
            
            for aluno in alunos:
                id_str = str(aluno["_id"])
                dias_almocou = 0
                dias_nao_almocou = 0
                
                for r in registros:
                    if id_str in r.get("nao_almocaram", []):
                        dias_nao_almocou += 1
                    else:
                        dias_almocou += 1
                
                soma_nao_almocaram_turma += dias_nao_almocou
                pct_almocou = (dias_almocou / total_dias) * 100
                
                relatorio_data.append({
                    "Aluno": aluno["nome"],
                    "Dias Registrados": total_dias,
                    "Almoçou (Dias)": dias_almocou,
                    "Não Almoçou (Dias)": dias_nao_almocou,
                    "% Presença no Almoço": f"{pct_almocou:.1f}%"
                })
            
            df_relatorio = pd.DataFrame(relatorio_data)
            
            st.markdown(f"### Turma {turma_rel}")
            st.caption(f"Período: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")
            
            st.metric("Total de Alunos", len(alunos))
            st.metric("Dias com Registro", total_dias)
            st.metric("Ausências no Almoço", soma_nao_almocaram_turma)
            
            st.markdown("---")
            st.dataframe(df_relatorio, use_container_width=True)
            
            pdf_bytes = gerar_pdf_bytes(
                df_relatorio, 
                turma_rel, 
                data_inicio.strftime('%d/%m/%Y'), 
                data_fim.strftime('%d/%m/%Y'),
                soma_nao_almocaram_turma
            )
            
            st.download_button(
                label="📄 BAIXAR RELATÓRIO PDF",
                data=pdf_bytes,
                file_name=f"relatorio_{turma_rel}_{str_inicio}.pdf",
                mime="application/pdf",
                type="primary"
            )

# -------------------------------------------------------------------
# RODAPÉ Padrão
# -------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888888; font-size: 14px; padding-bottom: 20px;'>"
    "Desenvolvido por Sergio Santos"
    "</div>",
    unsafe_allow_html=True
)
