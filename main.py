import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from io import BytesIO
from scipy.integrate import trapz

# --- FUNÇÕES AUXILIARES DE INTERFACE ---

def formatar_colunas(df):
    """Retorna lista de colunas para facilitar a seleção."""
    return df.columns.tolist()

# --- FUNÇÕES DE PROCESSAMENTO (BACKEND) ---

@st.cache_data
def carregar_dados_brutos(uploaded_files):
    """Leitura inicial sem processamento para identificar estrutura."""
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
    """
    Mescla uma ou mais colunas selecionadas pelo usuário em uma única 
    coluna 'TEMPO' do tipo datetime.
    """
    df = df.copy()
    if not colunas_tempo:
        return df

    try:
        if len(colunas_tempo) > 1:
            # Mescla múltiplas colunas (ex: Data + Hora) em uma string única
            string_tempo = df[colunas_tempo].astype(str).agg(' '.join, axis=1)
            df.insert(0, 'TEMPO', pd.to_datetime(string_tempo, dayfirst=True))
        else:
            # Apenas uma coluna de referência
            df.insert(0, 'TEMPO', pd.to_datetime(df[colunas_tempo[0]].astype(str), dayfirst=True))
        
        # Remove as colunas originais que foram mescladas para evitar redundância
        return df.drop(columns=colunas_tempo)
    except Exception as e:
        st.error(f"Erro ao converter colunas de tempo: {e}")
        return pd.DataFrame()

# --- INTERFACE PRINCIPAL ---

def main():
    st.set_page_config(page_title="Integralização Modular", layout="wide")
    st.title("📊 Processador de Dados Temporais")

    tabs = st.tabs(['📁 1. Importação e Tempo', '⚙️ 2. Filtros e Cálculo', '📈 3. Visualização'])

    # --- TAB 1: ESTRUTURA E TEMPO ---
    with tabs[0]:
        uploaded_files = st.file_uploader("Upload de Arquivos", type=["xlsx", "xls", "csv"], accept_multiple_files=True)
        
        if uploaded_files:
            dados_brutos = carregar_dados_brutos(uploaded_files)
            todas_colunas = formatar_colunas(dados_brutos)
            
            st.subheader("Configuração de Tempo")
            col_t1, col_t2 = st.columns([2, 1])
            
            with col_t1:
                colunas_tempo = st.multiselect(
                    "Selecione a(s) coluna(s) de referência temporal (serão mescladas):",
                    options=todas_colunas,
                    help="Selecione 'Data' e 'Hora' se estiverem separadas."
                )
            
            if colunas_tempo:
                dados_com_tempo = processar_datetime_custom(dados_brutos, colunas_tempo)
                if not dados_com_tempo.empty:
                    st.success("Coluna 'TEMPO' gerada com sucesso.")
                    st.dataframe(dados_com_tempo.head(5))
            else:
                st.info("Aguardando seleção das colunas de tempo...")
                dados_com_tempo = pd.DataFrame()
        else:
            dados_com_tempo = pd.DataFrame()

    # --- TAB 2: SELEÇÃO DE DADOS E CÁLCULO ---
    if not dados_com_tempo.empty:
        with tabs[1]:
            st.subheader("Seleção de Variáveis e Processamento")
            col_v1, col_v2 = st.columns(2)
            
            colunas_analise = [c for c in dados_com_tempo.columns if c != 'TEMPO']
            
            with col_v1:
                selecionadas = st.multiselect("Variáveis para integralizar:", options=colunas_analise, default=colunas_analise[:1])
                metodo = st.selectbox('Modo:', ['Média', 'Integralização'])
            
            with col_v2:
                periodo = st.number_input('Intervalo:', min_value=1, value=15)
                unidade = st.radio('Unidade:', ['s', 'min', 'h'], horizontal=True)
                excluir_nans = st.checkbox("Remover linhas vazias", value=True)

            if selecionadas:
                freq = f"{periodo}{unidade}"
                # Prepara DataFrame apenas com o necessário
                df_aux = dados_com_tempo[['TEMPO'] + selecionadas].set_index('TEMPO').sort_index()
                
                resampler = df_aux.resample(freq)
                
                if metodo == 'Média':
                    df_res = resampler.mean()
                else:
                    # Aplica a integral trapezoidal coluna por coluna
                    df_res = resampler.apply(lambda x: trapz(x) if len(x) > 1 else x.mean())

                if excluir_nans:
                    df_res = df_res.dropna()
                
                df_res = df_res.reset_index()
                st.write("### Resultado Processado")
                st.dataframe(df_res)
                
                # Botões de Download
                c1, c2 = st.columns(2)
                c1.download_button("Exportar CSV", df_res.to_csv(index=False).encode('utf-8'), "resultado.csv")
            else:
                st.warning("Selecione ao menos uma variável de análise.")

        # --- TAB 3: VISUALIZAÇÃO ---
        with tabs[2]:
            if selecionadas:
                var_plot = st.selectbox("Escolha a variável para o gráfico:", selecionadas)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=dados_com_tempo['TEMPO'], y=dados_com_tempo[var_plot], 
                                         name='Bruto', line=dict(color='silver', width=1)))
                fig.add_trace(go.Scatter(x=df_res['TEMPO'], y=df_res[var_plot], 
                                         name='Processado', line=dict(color='orange', width=2)))
                
                fig.update_layout(title=f"Análise de {var_plot}", template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
