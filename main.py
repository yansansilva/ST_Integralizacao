import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from io import BytesIO
from scipy.integrate import trapz

# --- FUNÇÕES DE PROCESSAMENTO (BACKEND) ---

@st.cache_data
def carregar_dados_brutos(uploaded_files):
    """Leitura inicial para identificar estrutura."""
    if not uploaded_files:
        return pd.DataFrame()
    
    lista_dfs = []
    for file in uploaded_files:
        file.seek(0)
        try:
            df = pd.read_csv(file, sep=';', decimal=',')
        except:
            df = pd.read_excel(file)
        lista_dfs.append(df)
    
    return pd.concat(lista_dfs).reset_index(drop=True) if lista_dfs else pd.DataFrame()

def processar_datetime_custom(df, colunas_tempo):
    """Mescla colunas de tempo selecionadas pelo usuário."""
    df = df.copy()
    if not colunas_tempo:
        return df
    try:
        if len(colunas_tempo) > 1:
            string_tempo = df[colunas_tempo].astype(str).agg(' '.join, axis=1)
            df.insert(0, 'TEMPO', pd.to_datetime(string_tempo, dayfirst=True))
        else:
            df.insert(0, 'TEMPO', pd.to_datetime(df[colunas_tempo[0]].astype(str), dayfirst=True))
        return df.drop(columns=colunas_tempo)
    except Exception as e:
        st.error(f"Erro na conversão de tempo: {e}")
        return pd.DataFrame()

def preparar_excel(df):
    """Gera o arquivo Excel em memória para download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados_Integralizados')
    return output.getvalue()

# --- INTERFACE PRINCIPAL ---

def main():
    st.set_page_config(page_title="Integralização de Dados", layout="wide")
    st.title("📊 Processador de Dados")

    tabs = st.tabs(['📁 1. Configurar Tempo', '⚙️ 2. Processar', '📈 3. Resultados'])

    # --- TAB 1: CARREGAMENTO E TEMPO ---
    with tabs[0]:
        uploaded_files = st.file_uploader("Upload de Arquivos", type=["xlsx", "xls", "csv"], accept_multiple_files=True)
        
        if uploaded_files:
            df_bruto = carregar_dados_brutos(uploaded_files)
            todas_colunas = df_bruto.columns.tolist()
            
            st.subheader("Referência Temporal")
            colunas_tempo = st.multiselect(
                "Selecione a(s) coluna(s) que compõem a data/hora:",
                options=todas_colunas,
                help="Ex: Selecione 'Data' e 'Hora' se estiverem separadas em colunas diferentes."
            )
            
            if colunas_tempo:
                dados_prontos = processar_datetime_custom(df_bruto, colunas_tempo)
                if not dados_prontos.empty:
                    st.success("Tempo configurado com sucesso!")
                    st.dataframe(dados_prontos.head(5))
            else:
                st.info("Aguardando definição das colunas de tempo.")
                dados_prontos = pd.DataFrame()
        else:
            dados_prontos = pd.DataFrame()

    # --- TAB 2: SELEÇÃO E CÁLCULO ---
    if not dados_prontos.empty:
        with tabs[1]:
            st.subheader("Configurações de Integralização")
            col_v1, col_v2 = st.columns(2)
            
            colunas_analise = [c for c in dados_prontos.columns if c != 'TEMPO']
            
            with col_v1:
                selecionadas = st.multiselect("Variáveis (Corrente, Tensão, Potência, etc):", options=colunas_analise)
                metodo = st.selectbox('Modo de cálculo:', ['Média', 'Integralização (Trapezoidal)'])
            
            with col_v2:
                freq_val = st.number_input('Intervalo numérico:', min_value=1, value=15)
                unidade = st.radio('Unidade de tempo:', ['s', 'min', 'h'], horizontal=True)
                excluir = st.checkbox("Remover linhas vazias (NaN)", value=True)

            if selecionadas:
                freq_str = f"{freq_val}{unidade}"
                df_calc = dados_prontos[['TEMPO'] + selecionadas].set_index('TEMPO').sort_index()
                resampler = df_calc.resample(freq_str)
                
                if "Média" in metodo:
                    df_res = resampler.mean()
                else:
                    df_res = resampler.apply(lambda x: trapz(x) if len(x) > 1 else x.mean())

                if excluir: df_res = df_res.dropna()
                df_res = df_res.reset_index()

                st.divider()
                st.subheader("📥 Download dos Resultados")
                nome_base = st.text_input("Nome do arquivo (sem extensão):", "resultado_processado")
                
                c_csv, c_xlsx = st.columns(2)
                
                # Download CSV
                c_csv.download_button(
                    label="Baixar em CSV",
                    data=df_res.to_csv(index=False).encode('utf-8'),
                    file_name=f"{nome_base}.csv",
                    mime='text/csv'
                )
                
                # Download XLSX
                c_xlsx.download_button(
                    label="Baixar em Excel (XLSX)",
                    data=preparar_excel(df_res),
                    file_name=f"{nome_base}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

                st.dataframe(df_res)

        # --- TAB 3: VISUALIZAÇÃO ---
        with tabs[2]:
            if selecionadas:
                escolha = st.selectbox("Selecione a variável para o gráfico:", selecionadas)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=dados_prontos['TEMPO'], y=dados_prontos[escolha], name='Bruto', line=dict(color='lightgrey')))
                fig.add_trace(go.Scatter(x=df_res['TEMPO'], y=df_res[escolha], name='Processado', line=dict(color='blue')))
                st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
