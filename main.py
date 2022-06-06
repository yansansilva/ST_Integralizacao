import streamlit as st
import pandas as pd
from io import BytesIO
import xlsxwriter
import openpyxl

@st.cache
def carregar_dados(up):
	dados_df = pd.DataFrame()
	for data_file in up:
		if data_file.type != "text/csv":
			df = pd.read_excel(data_file)
		else:
			df = pd.read_csv(data_file, sep=';', decimal=',')

		df['DATE'] = df['DATE'].astype('string')
		df['TIME'] = df['TIME'].astype('string')
		juntar = df['DATE'] + ' ' + df['TIME']
		df.insert(0, 'TEMPO', pd.to_datetime(juntar, dayfirst=True), True)

		dados_df = dados_df.append(df)

	return dados_df

@st.cache
def converter_df_csv(df):
	# IMPORTANT: Cache the conversion to prevent computation on every rerun
	return df.to_csv(index=False).encode('utf-8')

@st.cache
def converter_df_excel(df):
	output = BytesIO()
	writer = pd.ExcelWriter(output, engine='xlsxwriter')
	df.to_excel(writer, index=False, sheet_name='Plan1')
	workbook = writer.book
	worksheet = writer.sheets['Plan1']
	format1 = workbook.add_format({'num_format': '0.00'})
	worksheet.set_column('A:A', None, format1)
	writer.save()
	processed_data = output.getvalue()
	return processed_data

uploaded_files = st.sidebar.file_uploader("Upload Arquivos", type=["xlsx", "xls", "csv"], accept_multiple_files=True)

up = []
for file in uploaded_files:
	if file.name not in str(up):
		up.append(file)

dados = carregar_dados(up).drop(['DATE','TIME'], axis =1)

if dados.size != 0:
	filtro = st.sidebar.multiselect('Selecione as colunas de dados:', dados.columns)

	if filtro != []:
		dados_filtrados = dados.filter(items=filtro).sort_values(by=['TEMPO'], ignore_index=True)
		mostrar_dataset = st.checkbox('Mostrar Dataset')
		if mostrar_dataset == True:
			st.subheader("Dataset Original")
			st.dataframe(dados_filtrados)

		periodo = str(int(st.sidebar.number_input('Período de integralização:', min_value=1)))
		unidadetempo = st.sidebar.radio('Selecione a unidade de tempo:', ['Segundo(s)', 'Minuto(s)', 'Hora(s)'])
		if unidadetempo == 'Segundo(s)':
			unidade_de_periodo = 's'
		elif unidadetempo == 'Minuto(s)':
			unidade_de_periodo = 'min'
		elif unidadetempo == 'Hora(s)':
			unidade_de_periodo = 'h'


		integralizacao = periodo+unidade_de_periodo
		novo_dados_integralizacao = dados_filtrados.groupby('TEMPO').mean()
		dados_integralizados = novo_dados_integralizacao.resample(integralizacao).mean().dropna().reset_index()

		dados_integralizados.insert(1, 'DATE', dados_integralizados['TEMPO'].dt.date)
		dados_integralizados.insert(2, 'TIME', dados_integralizados['TEMPO'].dt.time.astype('str'))
		dados_integralizados.rename(columns={'TEMPO': 'REF'}, inplace=True)

		mostrar_resultado = st.checkbox('Mostrar resultado')
		if mostrar_resultado == True:
			st.subheader("Resultados")
			st.dataframe(dados_integralizados)

		st.subheader("Salvar Resultados")

		nomearquivo = st.text_input('Digite um nome para o arquivo:', 'Integralização')

		csv = converter_df_csv(dados_integralizados)
		st.download_button(label="Download em CSV", data=csv, file_name=nomearquivo+'.csv', mime='text/csv')

		excel = converter_df_excel(dados_integralizados)
		st.download_button(label="Download em Excel", data=excel, file_name=nomearquivo+'.xlsx', mime='application/vnd.ms-excel')
