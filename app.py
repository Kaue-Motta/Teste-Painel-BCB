import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import urllib3
import urllib3
from urllib3.util import Retry
import io
from datetime import datetime
import pytz

# 1. Configurações Iniciais e Segurança
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="Painel de Crédito - BCB", layout="wide")

# --- DICIONÁRIO DE SÉRIES ---
SERIES = {
    "Concessões Dessaz": {
        "Total": 24439, "PF": 24441, "PJ": 24440,
        "Livre Total": 24442, "Livre PF": 24444, "Livre PJ": 24443,
        "Direcionado Total": 24445, "Direcionado PF": 24447, "Direcionado PJ": 24446
    },
    "Concessões": {
        "Total": 20631, "PF": 20633, "PJ": 20632,
        "Livre Total": 20634, "Livre PF": 20662, "Livre PJ": 20635,
        "Direcionado Total": 20685, "Direcionado PF": 20698, "Direcionado PJ": 20686
    },
    "Saldo": {
        "Total": 20539, "PF": 20540, "PJ": 20541,
        "Livre Total": 20542, "Livre PF": 20570, "Livre PJ": 20543,
        "Direcionado Total": 20593, "Direcionado PF": 20606, "Direcionado PJ": 20594
    },
    "Juros": {
        "Total": 20714, "PF": 20716, "PJ": 20715,
        "Livre Total": 20717, "Livre PF": 20740, "Livre PJ": 20718,
        "Direcionado Total": 20756, "Direcionado PF": 20768, "Direcionado PJ": 20757
    },
    "Juros PF Detalhado": {
        "Cheque Especial": 20741,
        "Crédito Pessoal Total": 20748,
        "Consignado Total": 20747,
        "Consignado Público": 20745,
        "Consignado Privado": 20744,
        "Consignado INSS": 20746,
        "Não Consignado": 20742,
        "Veículos": 20749,
        "Aquisição de bens": 20751,
        "Arrendamento Mercantil": 20754,
        "Desconto de Cheques": 20755,
        "Cartão Rotativo": 22022,
        "Cartão Parcelado": 22023,
        "Cartão Total": 22024
    },
    "Macro": {
        "Selic": 4390
    },
    "Inadimplência": {
        "Total": 21082, "PF": 21084, "PJ": 21083, 
        "Livre Total": 21085, "Livre PF": 21112, "Livre PJ": 21086,
        "Direcionado Total": 21132, "Direcionado PF": 21145, "Direcionado PJ": 21133
    },
    "Inadimplência_Modalidades_PF": {
    "Inadimplência Livre PF – Cheque especial": 21113,
    "Inadimplência Livre PF – Não consignado": 21114,
    "Inadimplência Livre PF – Consignado privado": 21116,
    "Inadimplência Livre PF – Consignado público": 21117,
    "Inadimplência Livre PF – Consignado INSS": 21118,
    "Inadimplência Livre PF – Consignado total": 21119,
    "Inadimplência Livre PF – Crédito pessoal": 21120,
    "Inadimplência Livre PF – Veículos": 21121,
    "Inadimplência Livre PF – Aquisição de bens": 21123,
    "Inadimplência Livre PF – Arrendamento mercantil": 21126,
    "Inadimplência Livre PF – Crédito rotativo": 21127,
    "Inadimplência Livre PF – Cartão parcelado": 21128,
    "Inadimplência Livre PF – Cartão de crédito": 21129,
    "Inadimplência Livre PF – Desconto de cheques": 21130
    }
}

@st.cache_data(show_spinner=False, ttl=18000) 
def carregando_dados():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    # 1. Preparação da barra de progresso
    total_series = sum(len(sub) for sub in SERIES.values())
    progresso_bar = st.progress(0)
    status_text = st.empty() # Espaço para texto dinâmico
    contador = 0
    
    lista_dfs = []
    for categoria, subseries in SERIES.items():
        for nome, codigo in subseries.items():
            contador += 1
            # Atualiza a barra e o texto
            percentual = int((contador / total_series) * 100)
            progresso_bar.progress(percentual)
            status_text.info(f"📥 Acessando API do Banco Central: {categoria} - {nome} ({contador}/{total_series})")

            url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=01/01/2015"
            try:
                response = session.get(url, verify=False, timeout=30)
                if response.status_code == 200:
                    dados_json = response.json()
                    if dados_json:
                        df_temp = pd.DataFrame(dados_json)
                        df_temp['data'] = pd.to_datetime(df_temp['data'], dayfirst=True)
                        df_temp['valor'] = pd.to_numeric(df_temp['valor'])
                        df_temp = df_temp.set_index('data')
                        df_temp.columns = [f"{categoria} - {nome}"]
                        lista_dfs.append(df_temp)
            except Exception:
                continue
                
    # Limpa a barra e o texto após terminar
    progresso_bar.empty()
    status_text.empty()

    if not lista_dfs:
        st.error("Nenhum dado foi baixado.")
        st.stop()

    df_final = pd.concat(lista_dfs, axis=1)
    df_final = df_final.dropna(how='all') 
    df_final.index.name = None 
    return df_final

def formatar_brl(valor):
    try:
        return f"R$ {valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "N/A"

# Execução do carregamento
df_bruto = carregando_dados()

# --- LOG DE ATUALIZAÇÃO ---

# Define o fuso horário de Brasília
timezone = pytz.timezone('America/Sao_Paulo')
data_atualizacao = datetime.now(timezone).strftime('%d/%m/%Y %H:%M:%S')

# Exibe na barra lateral
st.sidebar.markdown("---")
st.sidebar.caption(f"✨ **Última atualização (SGS/BCB):**\n{data_atualizacao}")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Período")
if df_bruto.empty:
    st.stop()

datas_disponiveis = df_bruto.index.sort_values()
min_data = datas_disponiveis.min().to_pydatetime()
max_data = datas_disponiveis.max().to_pydatetime()

data_inicio, data_fim = st.sidebar.slider(
    "Selecione o período:",
    min_value=min_data, max_value=max_data,
    value=(min_data, max_data), format="MM/YYYY"
)

# Filtra mantendo a lógica original
df = df_bruto.loc[data_inicio:data_fim].copy()

# Botão de Download
st.sidebar.divider()
st.sidebar.subheader("📥 Exportar Dados")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Dados_Credito_BCB')
st.sidebar.download_button(
    label="Baixar Planilha (Excel)",
    data=buffer.getvalue(),
    file_name=f"dados_credito_{data_inicio.year}_{data_fim.year}.xlsx",
    mime="application/vnd.ms-excel"
)

# --- CORPO DO DASHBOARD ---
st.title("📊 Painel de Crédito - BCB")

try:
    tab_saldo, tab_concessoes, tab_juros, tab_inad = st.tabs([
        "💰 Saldo", "📈 Concessões", "🏦 Juros", "⚠️ Inadimplência"
    ])

# --- ABA: SALDO ---

    with tab_saldo:
        # 1. Última linha que REALMENTE tem o dado
        serie_valida = df["Saldo - Total"].dropna()
        
        if not serie_valida.empty:
            ultima_data_val = serie_valida.index[-1]
            ultima_data_formatada = ultima_data_val.strftime('%m/%Y')
            
            # Subset apenas com a linha da última data válida para as pizzas
            df_ultimo_val = df.loc[ultima_data_val]
            
            st.subheader(f"Saldo da Carteira ({data_inicio.year} - {data_fim.year})")       
            
            # --- CARTÕES DE MÉTRICAS (Saldo, MoM e YoY) ---
            idx_f = df_bruto.index.get_loc(ultima_data_val)
            
            # Valores para cálculo
            v_atual = df_bruto["Saldo - Total"].iloc[idx_f]
            v_mes_ant = df_bruto["Saldo - Total"].iloc[idx_f - 1]
            v_ano_ant = df_bruto["Saldo - Total"].iloc[idx_f - 12]
            
            # Cálculos das variações
            var_mom = ((v_atual / v_mes_ant) - 1) * 100
            var_yoy = ((v_atual / v_ano_ant) - 1) * 100
            
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Saldo Total ({ultima_data_formatada} - Mi)", formatar_brl(float(v_atual)))
            c2.metric("Variação Mensal (MoM)", f"{var_mom:+.2f}%")
            c3.metric("Variação Anual (YoY)", f"{var_yoy:+.2f}%")
            
            # Gráfico de evolução
            cols_saldo = [c for c in df.columns if "Saldo" in c]
            fig_saldo = px.line(df[cols_saldo], title="Evolução do Saldo (R$ Milhões)")
            st.plotly_chart(fig_saldo, use_container_width=True)

            st.divider()

            st.subheader(f"🎯 Estrutura do Mercado de Crédito em {ultima_data_formatada}")
            
            col_p1, col_p2, col_p3 = st.columns(3)
            
            with col_p1:
                # Agora busca-se o df_ultimo_val para garantir que não venha vazio
                v_direcionado = float(df_ultimo_val["Saldo - Direcionado Total"])
                v_livre = float(df_ultimo_val["Saldo - Livre Total"])
                fig1 = px.pie(names=["Crédito Direcionado", "Crédito Livre"], values=[v_direcionado, v_livre],
                              title="Composição: Origem do Recurso", hole=0.4,
                              color_discrete_sequence=["#1f77b4", "#ff7f0e"])
                st.plotly_chart(fig1, use_container_width=True)
                
            with col_p2:
                v_dir_pj = float(df_ultimo_val["Saldo - Direcionado PJ"])
                v_dir_pf = float(df_ultimo_val["Saldo - Direcionado PF"])
                fig2 = px.pie(names=["Direcionado PJ", "Direcionado PF"], values=[v_dir_pj, v_dir_pf],
                              title="Fatia do Crédito Direcionado", hole=0.4,
                              color_discrete_sequence=["#2ca02c", "#d62728"])
                st.plotly_chart(fig2, use_container_width=True)
                
            with col_p3:
                v_liv_pj = float(df_ultimo_val["Saldo - Livre PJ"])
                v_liv_pf = float(df_ultimo_val["Saldo - Livre PF"])
                fig3 = px.pie(names=["Livre PJ", "Livre PF"], values=[v_liv_pj, v_liv_pf],
                              title="Fatia do Crédito Livre", hole=0.4,
                              color_discrete_sequence=["#9467bd", "#8c564b"])
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("Nenhum dado de saldo encontrado para o período selecionado.")
        
        st.divider()

        st.subheader("📈 Dinâmica de Crescimento Ano a Ano (YoY)")
        st.markdown("Comparativo de aceleração dos últimos 6 meses (Variação % contra o mesmo mês do ano anterior).")

        # 1. Cálculo o YoY sobre o bruto
        df_yoy = df_bruto.pct_change(12) * 100
        
        # 2. FILTRO CRUCIAL: Remove linhas onde o Saldo Total é NaN antes de pegar os últimos 6
        # Isso garante que o gráfico pare antes de estar vazio
        df_yoy_valido = df_yoy[df_bruto["Saldo - Total"].notna()].copy()
        df_yoy_6m = df_yoy_valido.tail(6)
        
        # 3. Preparação para o gráfico (Reset e Formatação de data)
        df_yoy_6m.index.name = 'index'
        df_yoy_6m_reset = df_yoy_6m.reset_index()
        df_yoy_6m_reset['index'] = df_yoy_6m_reset['index'].dt.strftime('%b/%y')

        # --- GRÁFICO 1: VISÃO MACRO ---
        cols_macro = ["Saldo - Total", "Saldo - Direcionado Total", "Saldo - Livre Total"]
        yoy_macro = df_yoy_6m_reset.melt(id_vars='index', value_vars=cols_macro, var_name='Categoria', value_name='Crescimento %')
        yoy_macro['Categoria'] = yoy_macro['Categoria'].str.replace("Saldo - ", "")

        fig_macro = px.bar(
            yoy_macro, x='index', y='Crescimento %', color='Categoria',
            barmode='group', title="Crescimento YoY: Mercado Total vs Origem do Recurso",
            text_auto='.1f', labels={'index': 'Mês'},
            color_discrete_map={"Total": "#3366CC", "Direcionado Total": "#109618", "Livre Total": "#FF9900"}
        )
        st.plotly_chart(fig_macro, use_container_width=True)

        # --- SEGUNDA LINHA: DETALHAMENTO PF/PJ ---
        col_yoy_dir, col_yoy_liv = st.columns(2)

        with col_yoy_dir:
            cols_dir = ["Saldo - Direcionado PF", "Saldo - Direcionado PJ"]
            yoy_dir = df_yoy_6m_reset.melt(id_vars='index', value_vars=cols_dir, var_name='Modalidade', value_name='Crescimento %')
            yoy_dir['Modalidade'] = yoy_dir['Modalidade'].str.replace("Saldo - Direcionado ", "")

            fig_dir = px.bar(
                yoy_dir, x='index', y='Crescimento %', color='Modalidade',
                barmode='group', title="YoY: Detalhe Crédito Direcionado",
                text_auto='.1f', labels={'index': 'Mês'},
                color_discrete_sequence=["#66AA00", "#B82E2E"]
            )
            st.plotly_chart(fig_dir, use_container_width=True)

        with col_yoy_liv:
            cols_liv = ["Saldo - Livre PF", "Saldo - Livre PJ"]
            yoy_liv = df_yoy_6m_reset.melt(id_vars='index', value_vars=cols_liv, var_name='Modalidade', value_name='Crescimento %')
            yoy_liv['Modalidade'] = yoy_liv['Modalidade'].str.replace("Saldo - Livre ", "")

            fig_liv = px.bar(
                yoy_liv, x='index', y='Crescimento %', color='Modalidade',
                barmode='group', title="YoY: Detalhe Crédito Livre",
                text_auto='.1f', labels={'index': 'Mês'},
                color_discrete_sequence=["#FF9900", "#DD4477"]
            )
            st.plotly_chart(fig_liv, use_container_width=True)

        # --- RESUMO EXECUTIVO (INSIGHTS) ---
        st.divider()
        st.subheader("🤖 Insights da Análise de Saldo")
        
        try:
            # Captura os valores do último mês do DataFrame de barras (yoy_macro)
            # Usa 'Categoria' que é o nome definido no melt anterior
            ultimo_mes_yoy = yoy_macro[yoy_macro['index'] == yoy_macro['index'].iloc[-1]]
            
            crescimento_total = ultimo_mes_yoy[ultimo_mes_yoy['Categoria'] == 'Total']['Crescimento %'].values[0]
            crescimento_livre = ultimo_mes_yoy[ultimo_mes_yoy['Categoria'] == 'Livre Total']['Crescimento %'].values[0]
            crescimento_dir = ultimo_mes_yoy[ultimo_mes_yoy['Categoria'] == 'Direcionado Total']['Crescimento %'].values[0]
            
            # Cálculos de estrutura (usando os valores das pizzas)
            total_estoque = v_livre + v_direcionado
            p_livre = (v_livre / total_estoque) * 100
            p_dir = (v_direcionado / total_estoque) * 100
            
            # Lógica narrativa
            status = "expansão" if crescimento_total > 0 else "contração"
            motor = "Crédito Livre" if crescimento_livre > crescimento_dir else "Crédito Direcionado"
            
            col_i1, col_i2 = st.columns([1, 2])
            
            with col_i1:
                st.info(f"**Data base:** {ultima_data_formatada}")
                st.write(f"**Dominância:** {'Livre' if p_livre > p_dir else 'Direcionado'}")
            
            with col_i2:
                texto_insight = f"""
                O mercado de crédito encerrou o período em **{status}**, com um crescimento consolidado de **{crescimento_total:.1f}%** na comparação anual. 
                
                O principal motor de desempenho atual é o **{motor}**, que apresenta variação de **{max(crescimento_livre, crescimento_dir):.1f}%**. 
                Atualmente, o estoque de crédito livre representa **{p_livre:.1f}%** de toda a liquidez do sistema para este perfil de dados.
                """
                st.write(texto_insight)
                
        except Exception as e:
            st.write("Aguardando carregamento completo dos dados para gerar insights.")


# --- ABA: CONCESSÕES ---
    with tab_concessoes:
        # 1. Identificar a última data válida especificamente para Concessões
        serie_concessoes_valida = df["Concessões - Total"].dropna()
        
        if not serie_concessoes_valida.empty:
            ultima_data_conc = serie_concessoes_valida.index[-1]
            ultima_data_str = ultima_data_conc.strftime('%m/%Y')
            df_ult_conc = df.loc[ultima_data_conc] # Linha mestre para pizzas e métricas

            st.subheader(f"📈 Dinâmica das Novas Concessões ({ultima_data_str})")

            # --- MÉTRICAS DE DESTAQUE (TOP CARDS) ---
            idx_final = df_bruto.index.get_loc(ultima_data_conc)
            
            # Cálculos base para o Total
            v_atual_dsz = df_bruto["Concessões Dessaz - Total"].iloc[idx_final]
            v_ant_dsz = df_bruto["Concessões Dessaz - Total"].iloc[idx_final - 1]
            v_atual_orig = df_bruto["Concessões - Total"].iloc[idx_final]
            v_ano_ant_orig = df_bruto["Concessões - Total"].iloc[idx_final - 12]
            
            # Cálculos de Ciclo 12m
            s_12m_at = df_bruto["Concessões - Total"].rolling(12).sum().iloc[idx_final]
            s_12m_ant = df_bruto["Concessões - Total"].rolling(12).sum().iloc[idx_final - 12]

            # Variações Percentuais
            m_mom = ((v_atual_dsz / v_ant_dsz) - 1) * 100
            m_yoy = ((v_atual_orig / v_ano_ant_orig) - 1) * 100
            m_ciclo = ((s_12m_at / s_12m_ant) - 1) * 100

            # Exibição das métricas em colunas
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Volume Mensal (Dsz - Mi)", formatar_brl(v_atual_dsz))
            m2.metric("Variação MoM", f"{m_mom:+.2f}%")
            m3.metric("Variação YoY", f"{m_yoy:+.2f}%")
            m4.metric("Ciclo 12m", f"{m_ciclo:+.2f}%")
            
            st.divider()

            # --- 1. GRÁFICO DE TENDÊNCIA ESTRUTURAL (CICLO 12M) ---
            st.markdown("### 📊 Variação Acumulada em 12 Meses (Ciclo Anual)")
            
            cols_originais = ["Concessões - Total", "Concessões - PF", "Concessões - PJ"]
            soma_12m = df_bruto[cols_originais].rolling(window=12).sum()
            soma_12m_anterior = soma_12m.shift(12)
            df_ciclo = ((soma_12m / soma_12m_anterior) - 1) * 100
            
            # Filtra nulos para garantir que a linha do gráfico não caia para zero
            df_ciclo_filtrado = df_ciclo.loc[data_inicio:ultima_data_conc].dropna()

            fig_ciclo = px.line(
                df_ciclo_filtrado,
                title="Crescimento do Mercado (Média 12m vs 12m Anterior)",
                labels={"value": "Variação %", "index": "Mês"},
                color_discrete_sequence=px.colors.qualitative.T10
            )
            fig_ciclo.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_ciclo, use_container_width=True)

            # --- 2. TRÊS GRÁFICOS DE PIZZA (USANDO df_ult_conc) ---
            st.divider()
            st.markdown(f"### 🎯 Composição das Concessões ({ultima_data_str})")
            col_p1, col_p2, col_p3 = st.columns(3)

            with col_p1:
                v_livre = float(df_ult_conc["Concessões - Livre Total"])
                v_dir = float(df_ult_conc["Concessões - Direcionado Total"])
                fig1 = px.pie(names=["Livre", "Direcionado"], values=[v_livre, v_dir],
                              title="Total: Origem", hole=0.4, color_discrete_sequence=["#FF9900", "#109618"])
                st.plotly_chart(fig1, use_container_width=True)

            with col_p2:
                v_lpf = float(df_ult_conc["Concessões - Livre PF"])
                v_lpj = float(df_ult_conc["Concessões - Livre PJ"])
                fig2 = px.pie(names=["Livre PF", "Livre PJ"], values=[v_lpf, v_lpj],
                              title="Fatia do Crédito Livre", hole=0.4, color_discrete_sequence=["#FDCA54", "#FF9900"])
                st.plotly_chart(fig2, use_container_width=True)

            with col_p3:
                v_dpf = float(df_ult_conc["Concessões - Direcionado PF"])
                v_dpj = float(df_ult_conc["Concessões - Direcionado PJ"])
                fig3 = px.pie(names=["Dir. PF", "Dir. PJ"], values=[v_dpf, v_dpj],
                              title="Fatia do Crédito Direcionado", hole=0.4, color_discrete_sequence=["#66AA00", "#109618"])
                st.plotly_chart(fig3, use_container_width=True)

            # --- 3. VARIAÇÃO MENSAL (MoM DESSAZONALIZADA) ---
            st.divider()
            st.markdown("### ⚡ Variação Mensal Dessazonalizada (MoM)")
            cols_dessaz = [c for c in df.columns if "Concessões Dessaz" in c]
            
            # Pega os dados até a última data válida para o cálculo MoM
            df_mom_data = df.loc[:ultima_data_conc, cols_dessaz].tail(2)
            df_mom = df_mom_data.pct_change() * 100
            
            ult_mom = df_mom.tail(1).T.reset_index()
            ult_mom.columns = ['Série', 'Variação %']
            ult_mom['Série'] = ult_mom['Série'].str.replace("Concessões Dessaz - ", "")

            fig_mom = px.bar(ult_mom, x='Série', y='Variação %', text_auto='.1f',
                             color='Variação %', color_continuous_scale='RdYlGn',
                             title=f"Desempenho na Margem vs Mês Anterior ({ultima_data_str})")
            st.plotly_chart(fig_mom, use_container_width=True)

            # --- 4. TABELA RESUMO EXECUTIVO ---
            st.divider()
            st.subheader(f"📋 Resumo Executivo - {ultima_data_str}")

            def preparar_tabela_final():
                categorias = {
                    "Total": {"orig": "Concessões - Total", "dessaz": "Concessões Dessaz - Total"},
                    "PF": {"orig": "Concessões - PF", "dessaz": "Concessões Dessaz - PF"},
                    "PJ": {"orig": "Concessões - PJ", "dessaz": "Concessões Dessaz - PJ"},
                    "Livre Total": {"orig": "Concessões - Livre Total", "dessaz": "Concessões Dessaz - Livre Total"},
                    "Livre PF": {"orig": "Concessões - Livre PF", "dessaz": "Concessões Dessaz - Livre PF"},
                    "Livre PJ": {"orig": "Concessões - Livre PJ", "dessaz": "Concessões Dessaz - Livre PJ"},
                    "Direcionado Total": {"orig": "Concessões - Direcionado Total", "dessaz": "Concessões Dessaz - Direcionado Total"},
                    "Direcionado PF": {"orig": "Concessões - Direcionado PF", "dessaz": "Concessões Dessaz - Direcionado PF"},
                    "Direcionado PJ": {"orig": "Concessões - Direcionado PJ", "dessaz": "Concessões Dessaz - Direcionado PJ"}
                }
                linhas = []
                # Localiza o índice numérico da última data válida no df_bruto para os deslocamentos (shift)
                idx_final = df_bruto.index.get_loc(ultima_data_conc)
                
                for nome, fontes in categorias.items():
                    # Usa iloc com base no idx_final para evitar pegar 2026 vazio
                    atual_dsz = df_bruto[fontes["dessaz"]].iloc[idx_final]
                    anterior_dsz = df_bruto[fontes["dessaz"]].iloc[idx_final - 1]
                    atual_orig = df_bruto[fontes["orig"]].iloc[idx_final]
                    ano_passado_orig = df_bruto[fontes["orig"]].iloc[idx_final - 12]
                    
                    # Médias móveis para acum. 12m
                    soma_12m = df_bruto[fontes["orig"]].rolling(12).sum().iloc[idx_final]
                    soma_12m_ant = df_bruto[fontes["orig"]].rolling(12).sum().iloc[idx_final - 12]
                    
                    linhas.append({
                        "Variáveis": nome,
                        "Montante (R$ Mi - dessaz)": atual_dsz,
                        "Variação MoM - dessaz %": ((atual_dsz / anterior_dsz) - 1) * 100,
                        "Variação YoY %": ((atual_orig / ano_passado_orig) - 1) * 100,
                        "Acum. 12m %": ((soma_12m / soma_12m_ant) - 1) * 100
                    })
                return pd.DataFrame(linhas)

            df_resumo = preparar_tabela_final()

            st.dataframe(
                df_resumo.style.format({
                    "Montante (R$ Mi - dessaz)": "{:,.0f}",
                    "Variação MoM - dessaz %": "{:+.2f}%",
                    "Variação YoY %": "{:+.2f}%",
                    "Acum. 12m %": "{:+.2f}%"
                }).applymap(lambda x: 'color: green' if x > 0 else 'color: red',
                            subset=["Variação MoM - dessaz %", "Variação YoY %", "Acum. 12m %"]
                ).set_properties(**{'text-align': 'center'}),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("Dados de Concessões não disponíveis para o período.")

            # --- RESUMO EXECUTIVO (DINÂMICO) ---
        st.divider()
        st.subheader("🤖 Insights - Concessões")
        
        try:
            # Extrai os indicadores chave da tabela df_resumo para o texto
            # Pega a linha 'Total' para a visão macro
            dados_total = df_resumo[df_resumo['Variáveis'] == 'Total'].iloc[0]
            
            mom_val = dados_total['Variação MoM - dessaz %']
            yoy_val = dados_total['Variação YoY %']
            acum_12m = dados_total['Acum. 12m %']
            montante = dados_total['Montante (R$ Mi - dessaz)']
            
            # Lógica de interpretação
            sentido_mom = "expansão" if mom_val > 0 else "contração"
            sentido_yoy = "acelerou" if yoy_val > 0 else "recuou"
            
            # Identificar o maior crescimento nas subcategorias para destacar o "motor"
            df_subs = df_resumo[df_resumo['Variáveis'].isin(['Livre Total', 'Direcionado Total'])]
            motor_nome = df_subs.loc[df_subs['Variação YoY %'].idxmax()]['Variáveis']
            motor_val = df_subs['Variação YoY %'].max()

            insight_concessoes = f"""
            No mês de **{ultima_data_str}**, o fluxo de novas concessões atingiu o montante dessazonalizado de **R$ {montante:,.0f} milhões**. 
            Este resultado representa uma **{sentido_mom} de {abs(mom_val):.2f}%** em relação ao mês anterior (MoM).
            
            **Análise de Tendência:**
            * Comparado ao mesmo período do ano anterior (YoY), o mercado **{sentido_yoy} {abs(yoy_val):.2f}%**.
            * No ciclo acumulado de 12 meses, observa-se um crescimento de **{acum_12m:.2f}%**, indicando o fôlego do mercado a longo prazo.
            * O destaque positivo do período foi o segmento de **{motor_nome}**, com uma variação anual de **{motor_val:+.2f}%**, consolidando-se como o principal driver de liquidez no mês.
            
            **Conclusão:** O volume de novos créditos sugere um cenário de {"aquecimento" if mom_val > 0 and yoy_val > 0 else "cautela ou ajuste"} na margem, 
            sendo fundamental monitorar se a variação do crédito {motor_nome.lower()} continuará a sustentar o índice total nos próximos meses.
            """
            
            st.info(insight_concessoes)
            
        except Exception as e:
            st.warning("Não foi possível gerar os insights automáticos para os filtros selecionados.")


# --- ABA: JUROS ---
    with tab_juros:
        serie_juros_valida = df["Juros - Total"].dropna()
        
        if not serie_juros_valida.empty:
            ultima_data_j = serie_juros_valida.index[-1]
            ultima_data_j_str = ultima_data_j.strftime('%m/%Y')
            mes_anterior_j_str = (ultima_data_j - pd.DateOffset(months=1)).strftime('%m/%Y')
            df_ult_juros = df.loc[ultima_data_j] 

            st.subheader(f"📈 Taxas de Juros (% a.a.) - {ultima_data_j_str}")
            
            # --- LEGENDA DE VARIAÇÃO ---
            st.caption(f"Variações (delta) calculadas em relação a {mes_anterior_j_str}")

            # --- CARTÕES DE MÉTRICAS ---
            idx_j = df_bruto.index.get_loc(ultima_data_j)
            
            # Valores atuais
            j_total_at = float(df_bruto["Juros - Total"].iloc[idx_j])
            j_pf_at = float(df_bruto["Juros - PF"].iloc[idx_j])
            j_pj_at = float(df_bruto["Juros - PJ"].iloc[idx_j])
            
            # Valores mês anterior
            j_total_ant = float(df_bruto["Juros - Total"].iloc[idx_j - 1])
            j_pf_ant = float(df_bruto["Juros - PF"].iloc[idx_j - 1])
            j_pj_ant = float(df_bruto["Juros - PJ"].iloc[idx_j - 1])
            
            # Variações (p.p.)
            var_total_pp = j_total_at - j_total_ant
            var_pf_pp = j_pf_at - j_pf_ant
            var_pj_pp = j_pj_at - j_pj_ant

            mj1, mj2, mj3 = st.columns(3)
            mj1.metric("Taxa Média Total", f"{j_total_at:.2f}%", f"{var_total_pp:+.2f} p.p.", delta_color="inverse")
            mj2.metric("Taxa Média PF", f"{j_pf_at:.2f}%", f"{var_pf_pp:+.2f} p.p.", delta_color="inverse")
            mj3.metric("Taxa Média PJ", f"{j_pj_at:.2f}%", f"{var_pj_pp:+.2f} p.p.", delta_color="inverse")
            
            st.divider()

            # --- 1. EVOLUÇÃO GERAL ---
            cols_juros_base = ["Juros - Total", "Juros - PF", "Juros - PJ"]
            fig_juros = px.line(
                df[cols_juros_base].loc[data_inicio:ultima_data_j],
                title="Evolução das Taxas de Juros (Total, PF e PJ)",
                labels={"value": "Taxa % a.a.", "index": "Mês", "variable": "Série"}
            )
            fig_juros.update_layout(hovermode="x unified")
            st.plotly_chart(fig_juros, use_container_width=True)

            st.divider()

            # --- 2. COMPARAÇÃO POR NATUREZA E SEGMENTAÇÃO (VALOR INTERNO E BADGES AZUIS) ---
            st.subheader("⚖️ Juros por Natureza e Perfil")
            
            # Legenda de variação
            mes_anterior_j_str = (ultima_data_j - pd.DateOffset(months=1)).strftime('%m/%Y')
            st.caption(f"Os balões azuis indicam a variação mensal (MoM) em relação a {mes_anterior_j_str}")
            
            col_j1, col_j2 = st.columns(2)
            idx_j = df_bruto.index.get_loc(ultima_data_j)

            with col_j1:
                try:
                    # Mapeamento para Natureza
                    series_natureza = {
                        "Juros Direcionado": "Juros - Direcionado Total",
                        "Juros Total": "Juros - Total",
                        "Juros Livre": "Juros - Livre Total"
                    }
                    
                    dados_nat = []
                    for label, col_name in series_natureza.items():
                        v_at = float(df_bruto[col_name].iloc[idx_j])
                        v_ant = float(df_bruto[col_name].iloc[idx_j - 1])
                        v_pp = v_at - v_ant
                        
                        dados_nat.append({
                            "Natureza": label,
                            "Taxa": v_at,
                            "Valor_Interno": f"{v_at:.1f}%",
                            "Variacao_Externa": f"{v_pp:+.2f} pp"
                        })

                    df_natureza_plot = pd.DataFrame(dados_nat)

                    fig_natureza = px.bar(
                        df_natureza_plot, x='Taxa', y='Natureza', orientation='h',
                        title="Custo por Natureza",
                        text='Valor_Interno', color='Taxa',
                        color_continuous_scale=['#109618', '#FF9900', '#d62728']
                    )

                    for i, row in df_natureza_plot.iterrows():
                        fig_natureza.add_annotation(
                            x=row['Taxa'], y=row['Natureza'],
                            text=f"<b>{row['Variacao_Externa']}</b>",
                            showarrow=False, xanchor='left', xshift=12,
                            font=dict(color="white", size=10),
                            bgcolor="#1f77b4", bordercolor="#1f77b4",
                            borderwidth=1, borderpad=3, opacity=0.9
                        )

                    fig_natureza.update_layout(showlegend=False, xaxis_ticksuffix="%", coloraxis_showscale=False, height=350, margin=dict(r=100))
                    fig_natureza.update_traces(textposition='inside', textfont_size=12, textfont_color="white")
                    st.plotly_chart(fig_natureza, use_container_width=True)
                except:
                    st.info("Séries de Juros por Natureza não disponíveis.")

            with col_j2:
                try:
                    # Mapeamento para Perfil (Vertical)
                    series_perfil = {
                        "Livre PJ": "Juros - Livre PJ",
                        "Livre PF": "Juros - Livre PF"
                    }
                    
                    dados_perfil = []
                    for label, col_name in series_perfil.items():
                        v_at = float(df_bruto[col_name].iloc[idx_j])
                        v_ant = float(df_bruto[col_name].iloc[idx_j - 1])
                        v_pp = v_at - v_ant
                        
                        dados_perfil.append({
                            "Perfil": label,
                            "Taxa": v_at,
                            "Valor_Interno": f"{v_at:.1f}%",
                            "Variacao_Externa": f"{v_pp:+.2f} pp"
                        })

                    df_perfil_plot = pd.DataFrame(dados_perfil)

                    fig_perfil = px.bar(
                        df_perfil_plot, x='Taxa', y='Perfil', orientation='h',
                        title="Perfil do Crédito Livre",
                        text='Valor_Interno', color='Perfil',
                        color_discrete_map={"Livre PJ": "#1f77b4", "Livre PF": "#d62728"}
                    )

                    for i, row in df_perfil_plot.iterrows():
                        fig_perfil.add_annotation(
                            x=row['Taxa'], y=row['Perfil'],
                            text=f"<b>{row['Variacao_Externa']}</b>",
                            showarrow=False, xanchor='left', xshift=12,
                            font=dict(color="white", size=10),
                            bgcolor="#003366", bordercolor="#003366",
                            borderwidth=1, borderpad=3, opacity=0.9
                        )

                    fig_perfil.update_layout(showlegend=False, xaxis_ticksuffix="%", height=350, margin=dict(r=100))
                    fig_perfil.update_traces(textposition='inside', textfont_size=12, textfont_color="white")
                    st.plotly_chart(fig_perfil, use_container_width=True)
                except:
                    st.info("Séries de Perfil de Juros não disponíveis.")

            st.divider()

            # --- 3. DETALHAMENTO DINÂMICO: RANKING TOP 10 MAIORES TAXAS PF (COM VARIAÇÃO MoM) ---
            st.subheader("🎯 Hierarquia de Juros: Top 10 Detalhamento Livre PF")
            
            prefixo_pf = "Juros PF Detalhado - "
            colunas_detalhe = [c for c in df.columns if c.startswith(prefixo_pf)]

            dados_lista = []
            for col in colunas_detalhe:
                serie_limpa = df[col].dropna()
                # Necessário pelo menos 2 pontos para calcular a variação MoM
                if len(serie_limpa) >= 2:
                    val_atual = float(serie_limpa.iloc[-1])
                    val_anterior = float(serie_limpa.iloc[-2])
                    variacao_pp = val_atual - val_anterior
                    
                    if val_atual > 0:
                        dados_lista.append({
                            "Modalidade": col.replace(prefixo_pf, ""), 
                            "Taxa % a.a.": val_atual,
                            "Var. p.p.": variacao_pp,
                            # Rótulo customizado que aparecerá na barra
                            "Rotulo": f"{val_atual:.0f}%   ({variacao_pp:+.2f} pp)"
                        })

            if dados_lista:
                # Ordena e pega as 10 maiores taxas
                df_ranking_top = pd.DataFrame(dados_lista).sort_values(by="Taxa % a.a.", ascending=True).tail(10)

                fig_ranking = px.bar(
                    df_ranking_top, 
                    x='Taxa % a.a.', 
                    y='Modalidade',
                    orientation='h',
                    title=f"As 10 Modalidades PF mais Onerosas e Variação Mensal ({ultima_data_j_str})",
                    text='Rotulo', # Usa o rótulo customizado aqui
                    color='Taxa % a.a.',
                    color_continuous_scale='Reds'
                )
                
                fig_ranking.update_layout(
                    height=500, 
                    xaxis_ticksuffix="%",
                    coloraxis_showscale=False,
                    yaxis={'categoryorder':'total ascending'},
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                
                # Ajusta a posição do texto para fora ou dentro da barra automaticamente
                fig_ranking.update_traces(textposition='outside')
                
                st.plotly_chart(fig_ranking, use_container_width=True)
            else:
                st.info("Séries de detalhamento PF insuficientes para calcular variações recentes.")

            st.divider()

            # --- 4. TRANSMISSÃO DA POLÍTICA MONETÁRIA ---
            st.subheader("📡 Transmissão da Política Monetária")
            
            selic_mensal = df_bruto["Macro - Selic"] / 100
            df_bruto["Selic Anualizada"] = (((1 + selic_mensal)**12) - 1) * 100
            
            cols_trans = ["Juros - Livre Total", "Juros - Direcionado Total", "Selic Anualizada"]
            df_trans = df_bruto[cols_trans].loc[data_inicio:ultima_data_j].dropna()

            from plotly.subplots import make_subplots
            import plotly.graph_objects as go

            fig_trans = make_subplots(specs=[[{"secondary_y": True}]])
            fig_trans.add_trace(go.Scatter(x=df_trans.index, y=df_trans["Juros - Livre Total"], name="Juros Livre", line=dict(color='#d62728', width=3)), secondary_y=False)
            fig_trans.add_trace(go.Scatter(x=df_trans.index, y=df_trans["Juros - Direcionado Total"], name="Juros Direcionado", line=dict(color='#109618', width=2, dash='dot')), secondary_y=False)
            fig_trans.add_trace(go.Scatter(x=df_trans.index, y=df_trans["Selic Anualizada"], name="Selic (Eixo Dir.)", line=dict(color='black', width=3, dash='dash')), secondary_y=True)

            fig_trans.update_layout(title="Aderência dos Juros à Selic", hovermode="x unified")
            st.plotly_chart(fig_trans, use_container_width=True)

            st.divider()

            # --- 5. VARIAÇÃO YoY ---
            st.subheader("📉 Variação Interanual")
            cols_yoy = ["Juros - Livre PF", "Juros - Livre PJ"]
            df_yoy_pp_bruto = (df_bruto[cols_yoy] - df_bruto[cols_yoy].shift(12))
            df_ultimos_6 = df_yoy_pp_bruto.loc[:ultima_data_j].tail(6).copy()
            
            df_ultimos_6.index = df_ultimos_6.index.strftime('%b/%y')
            df_plot_yoy = df_ultimos_6.reset_index().melt(id_vars='index', var_name='Perfil', value_name='Variação p.p.')
            df_plot_yoy['Perfil'] = df_plot_yoy['Perfil'].str.replace("Juros - ", "")

            fig_yoy_pp = px.bar(
                df_plot_yoy, x='index', y='Variação p.p.', color='Perfil', barmode='group',
                title="Variação YoY em Pontos Percentuais (p.p.)",
                text_auto='.1f', color_discrete_map={"Livre PF": "#d62728", "Livre PJ": "#1f77b4"}
            )
            fig_yoy_pp.add_hline(y=0, line_dash="solid", line_color="black")
            st.plotly_chart(fig_yoy_pp, use_container_width=True)

            # --- 6. INSIGHTS DE JUROS ---
            st.divider()
            st.subheader("🤖 Insights - Juros")
            
            try:
                # Recuperando os valores para o texto do insight
                v_total_ins = float(df_ult_juros["Juros - Total"])
                v_livre_ins = float(df_ult_juros["Juros - Livre Total"])
                
                # Pegamos o último valor não nulo da variação YoY
                serie_yoy_pf = df_yoy_pp_bruto["Juros - Livre PF"].dropna()
                serie_yoy_pj = df_yoy_pp_bruto["Juros - Livre PJ"].dropna()

                var_pf_val = serie_yoy_pf.iloc[-1] if not serie_yoy_pf.empty else None
                var_pj_val = serie_yoy_pj.iloc[-1] if not serie_yoy_pj.empty else None
                
                selic_atual = df_trans["Selic Anualizada"].iloc[-1]
                
                def formatar_var(valor):
                    if valor is None or pd.isna(valor):
                        return "dados insuficientes"
                    return f"{valor:+.1f} p.p."

                txt_pf = formatar_var(var_pf_val)
                txt_pj = formatar_var(var_pj_val)

                if var_pf_val is not None and var_pj_val is not None:
                    status_juros = "queda" if var_pf_val < 0 and var_pj_val < 0 else "elevação ou estabilidade"
                else:
                    status_juros = "análise em andamento"
                
                st.info(f"""
                Em **{ultima_data_j_str}**, a taxa média de juros do mercado fechou em **{v_total_ins:.2f}% a.a.**
                
                **Destaques:**
                * O spread entre o Crédito Livre (**{v_livre_ins:.1f}%**) e a Selic Anualizada (**{selic_atual:.1f}%**) permanece elevado.
                * Na comparação anual (YoY), o custo para **PF** variou **{txt_pf}** e para **PJ** **{txt_pj}**.
                * A tendência recente para o custo do crédito é de **{status_juros}**.
                """)
            except Exception as e:
                st.write(f"Insights indisponíveis no momento. (Motivo: {e})")

    # --- ABA: INADIMPLÊNCIA ---
    with tab_inad:
        # 1. Identificar as datas para o cálculo de variação mensal
        serie_inad_valida = df["Inadimplência - Total"].dropna()
        
        if not serie_inad_valida.empty and len(serie_inad_valida) >= 2:
            # Datas
            ultima_data_inad = serie_inad_valida.index[-1]
            mes_anterior_inad = serie_inad_valida.index[-2]
            
            ultima_data_str = ultima_data_inad.strftime('%m/%Y')
            mes_anterior_str = mes_anterior_inad.strftime('%m/%Y')
            
            st.subheader(f"📊 Inadimplência (Acima de 90 dias) - {ultima_data_str}")
            st.caption(f"Variações (delta) calculadas em relação a {mes_anterior_str}")

            # 2. Métricas de Destaque com Delta (Variação Mensal)
            val_total_atual = float(df["Inadimplência - Total"].loc[ultima_data_inad])
            val_pf_atual = float(df["Inadimplência - PF"].loc[ultima_data_inad])
            val_pj_atual = float(df["Inadimplência - PJ"].loc[ultima_data_inad])
            
            val_total_ant = float(df["Inadimplência - Total"].loc[mes_anterior_inad])
            val_pf_ant = float(df["Inadimplência - PF"].loc[mes_anterior_inad])
            val_pj_ant = float(df["Inadimplência - PJ"].loc[mes_anterior_inad])

            col_m1, col_m2, col_m3 = st.columns(3)
            
            # delta_color="inverse": Positivo = Vermelho (piora), Negativo = Verde (melhora)
            col_m1.metric("Total", f"{val_total_atual:.2f}%", 
                          delta=f"{val_total_atual - val_total_ant:+.2f} p.p.", delta_color="inverse")
            
            col_m2.metric("Pessoa Física (PF)", f"{val_pf_atual:.2f}%", 
                          delta=f"{val_pf_atual - val_pf_ant:+.2f} p.p.", delta_color="inverse")
            
            col_m3.metric("Pessoa Jurídica (PJ)", f"{val_pj_atual:.2f}%", 
                          delta=f"{val_pj_atual - val_pj_ant:+.2f} p.p.", delta_color="inverse")

            st.divider()

            # 3. Gráfico de Evolução
            cols_evolucao = ["Inadimplência - Total", "Inadimplência - PF", "Inadimplência - PJ"]
            fig_inad = px.line(
                df[cols_evolucao].loc[data_inicio:ultima_data_inad],
                title="Evolução da Taxa de Inadimplência",
                labels={"value": "Índice (%)", "index": "Mês", "variable": "Segmento"},
                color_discrete_map={
                    "Inadimplência - Total": "#FF9900",
                    "Inadimplência - PF": "#d62728",
                    "Inadimplência - PJ": "#1f77b4"
                }
            )
            fig_inad.update_layout(hovermode="x unified")
            st.plotly_chart(fig_inad, use_container_width=True)

            st.divider()

           # 4. COMPARAÇÃO POR NATUREZA (VALORES INTERNOS E BADGES EXTERNOS)
            st.subheader("⚖️ Inadimplência por Natureza e Perfil")
            
            # --- LEGENDA DE VARIAÇÃO ---
            mes_anterior_inad_str = (ultima_data_inad - pd.DateOffset(months=1)).strftime('%m/%Y')
            st.caption(f"Os balões azuis indicam a variação mensal (MoM) em relação a {mes_anterior_inad_str}")

            col_i1, col_i2 = st.columns(2)

            idx_atual = df_bruto.index.get_loc(ultima_data_inad)
            
            with col_i1:
                try:
                    series_livre = {"Livre PJ": "Inadimplência - Livre PJ", "Livre Total": "Inadimplência - Livre Total", "Livre PF": "Inadimplência - Livre PF"}
                    dados_livre = []
                    for label, col_name in series_livre.items():
                        v_at = float(df_bruto[col_name].iloc[idx_atual])
                        v_ant = float(df_bruto[col_name].iloc[idx_atual - 1])
                        v_pp = v_at - v_ant
                        
                        dados_livre.append({
                            "Perfil": label,
                            "Inadimplência (%)": v_at,
                            "Valor_Interno": f"{v_at:.2f}%",
                            "Variacao_Externa": f"{v_pp:+.2f} pp"
                        })

                    df_livre_plot = pd.DataFrame(dados_livre)

                    fig_livre = px.bar(
                        df_livre_plot, x='Inadimplência (%)', y='Perfil', orientation='h',
                        title="Crédito Livre (Recursos Livres)", 
                        text='Valor_Interno', color='Perfil',
                        color_discrete_map={"Livre PJ": "#1f77b4", "Livre Total": "#7f7f7f", "Livre PF": "#d62728"}
                    )
                    
                    for i, row in df_livre_plot.iterrows():
                        fig_livre.add_annotation(
                            x=row['Inadimplência (%)'], y=row['Perfil'],
                            text=f"<b>{row['Variacao_Externa']}</b>",
                            showarrow=False, xanchor='left', xshift=12,
                            font=dict(color="white", size=10),
                            bgcolor="#1f77b4", bordercolor="#1f77b4",
                            borderwidth=1, borderpad=3, opacity=0.9
                        )

                    fig_livre.update_layout(showlegend=False, xaxis_ticksuffix="%", height=350, margin=dict(r=100))
                    fig_livre.update_traces(textposition='inside', textfont_size=12, textfont_color="white")
                    st.plotly_chart(fig_livre, use_container_width=True)
                except:
                    st.info("Séries de Inadimplência Livre não disponíveis.")

            with col_i2:
                try:
                    series_dir = {"Direcionado PJ": "Inadimplência - Direcionado PJ", "Direcionado Total": "Inadimplência - Direcionado Total", "Direcionado PF": "Inadimplência - Direcionado PF"}
                    dados_dir = []
                    for label, col_name in series_dir.items():
                        v_at = float(df_bruto[col_name].iloc[idx_atual])
                        v_ant = float(df_bruto[col_name].iloc[idx_atual - 1])
                        v_pp = v_at - v_ant
                        
                        dados_dir.append({
                            "Perfil": label,
                            "Inadimplência (%)": v_at,
                            "Valor_Interno": f"{v_at:.2f}%",
                            "Variacao_Externa": f"{v_pp:+.2f} pp"
                        })

                    df_dir_plot = pd.DataFrame(dados_dir)

                    fig_dir = px.bar(
                        df_dir_plot, x='Inadimplência (%)', y='Perfil', orientation='h',
                        title="Crédito Direcionado", 
                        text='Valor_Interno', color='Perfil',
                        color_discrete_map={"Direcionado PJ": "#9467bd", "Direcionado Total": "#c7c7c7", "Direcionado PF": "#bcbd22"}
                    )

                    for i, row in df_dir_plot.iterrows():
                        fig_dir.add_annotation(
                            x=row['Inadimplência (%)'], y=row['Perfil'],
                            text=f"<b>{row['Variacao_Externa']}</b>",
                            showarrow=False, xanchor='left', xshift=12,
                            font=dict(color="white", size=10),
                            bgcolor="#003366", bordercolor="#003366",
                            borderwidth=1, borderpad=3, opacity=0.9
                        )

                    fig_dir.update_layout(showlegend=False, xaxis_ticksuffix="%", height=350, margin=dict(r=100))
                    fig_dir.update_traces(textposition='inside', textfont_size=12, textfont_color="white")
                    st.plotly_chart(fig_dir, use_container_width=True)
                except:
                    st.info("Séries de Inadimplência Direcionada não disponíveis.")

            st.divider()

            # 5. VARIAÇÃO YoY (RECURSOS LIVRES)
            st.subheader("📉 Variação Interanual com Recursos Livres (YoY em p.p.)")
            cols_yoy_livre = ["Inadimplência - Livre PF", "Inadimplência - Livre PJ"]
            df_yoy_livre = (df_bruto[cols_yoy_livre] - df_bruto[cols_yoy_livre].shift(12))
            df_ultimos_6_livre = df_yoy_livre.loc[:ultima_data_inad].tail(6).copy()
            df_ultimos_6_livre.index = df_ultimos_6_livre.index.strftime('%b/%y')
            
            df_plot_livre_yoy = df_ultimos_6_livre.reset_index().melt(
                id_vars='index', var_name='Perfil', value_name='Variação p.p.'
            )
            df_plot_livre_yoy['Perfil'] = df_plot_livre_yoy['Perfil'].str.replace("Inadimplência - Livre ", "")

            fig_yoy_livre = px.bar(
                df_plot_livre_yoy, x='index', y='Variação p.p.', color='Perfil', barmode='group',
                title="Variação YoY (p.p.) - Recursos Livres",
                text_auto='.2f', color_discrete_map={"PF": "#d62728", "PJ": "#1f77b4"}
            )
            fig_yoy_livre.add_hline(y=0, line_dash="solid", line_color="black")
            st.plotly_chart(fig_yoy_livre, use_container_width=True)

            # --- 6. DETALHAMENTO POR MODALIDADE PF (TOP 10) ---
            st.divider()
            st.subheader("🔍 Top 10 Maiores Taxas de Inadimplência (Livre - PF)")
            
            # Criação de uma variável para armazenar o dataframe fora do try para o insight ler depois
            df_top10_insight = pd.DataFrame()

            try:
                cols_modalidades = [
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Cheque especial",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Não consignado",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Consignado privado",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Consignado público",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Consignado INSS",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Consignado total",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Crédito pessoal",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Veículos",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Aquisição de bens",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Arrendamento mercantil",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Crédito rotativo",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Cartão parcelado",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Cartão de crédito",
                    "Inadimplência_Modalidades_PF - Inadimplência Livre PF – Desconto de cheques"
                ]

                dados_lista = []
                for col in cols_modalidades:
                    if col in df.columns:
                        serie = df[col].dropna()
                        # Necessário 2 pontos para calcular a variação MoM
                        if len(serie) >= 2:
                            val_atual = float(serie.iloc[-1])
                            val_anterior = float(serie.iloc[-2])
                            variacao_pp = val_atual - val_anterior
                            
                            nome_limpo = col.split("–")[-1].strip()
                            dados_lista.append({
                                "Modalidade": nome_limpo, 
                                "Índice (%)": val_atual,
                                "Var. p.p.": variacao_pp,
                                "Rotulo": f"{val_atual:.1f}%   ({variacao_pp:+.2f} pp)"
                            })

                if dados_lista:
                    df_ranking = pd.DataFrame(dados_lista)
                    # Pega as 10 maiores e ordena para o gráfico de barras horizontais
                    df_top10_insight = df_ranking.nlargest(10, "Índice (%)").sort_values(by="Índice (%)", ascending=True)

                    fig_ranking = px.bar(
                        df_top10_insight, x='Índice (%)', y='Modalidade', orientation='h',
                        title=f"Top 10 Linhas Críticas e Variação Mensal ({ultima_data_str})",
                        text='Rotulo', # Rótulo customizado: Valor + Variação
                        color='Índice (%)', 
                        color_continuous_scale='Reds'
                    )

                    fig_ranking.update_layout(
                        showlegend=False, xaxis_ticksuffix="%", height=500,
                        coloraxis_showscale=False, margin=dict(l=20, r=20, t=50, b=20)
                    )
                    
                    fig_ranking.update_traces(textposition='outside')
                    
                    st.plotly_chart(fig_ranking, use_container_width=True)
                else:
                    st.info("Séries detalhadas de inadimplência insuficientes para calcular variações.")

            except Exception as e:
                st.error(f"Erro ao processar ranking: {e}")


            # --- 7. INSIGHTS AUTOMATIZADOS (Dentro do if de dados válidos) ---
            st.divider()
            st.subheader("💡 Insights do Painel de Inadimplência")

            var_pf = val_pf_atual - val_pf_ant
            
            c1, c2 = st.columns(2)

            with c1:
                st.info("**Análise de Segmento**")
                if var_pf > 0:
                    st.write(f"⚠️ A inadimplência PF subiu **{var_pf:+.2f} p.p.** no mês. Isso indica uma pressão maior sobre o orçamento doméstico.")
                else:
                    st.write(f"✅ A inadimplência PF recuou **{abs(var_pf):.2f} p.p.**, sugerindo uma melhora na saúde financeira das famílias.")

            with c2:
                st.info("**Foco no Risco**")
                if not df_top10_insight.empty:
                    maior_risco_nome = df_top10_insight.iloc[-1]['Modalidade']
                    maior_risco_val = df_top10_insight.iloc[-1]['Índice (%)']
                    st.write(f"🎯 O **{maior_risco_nome}** apresenta o maior risco do portfólio, com **{maior_risco_val:.1f}%** de inadimplência.")
                    if "Rotativo" in maior_risco_nome or "Cheque" in maior_risco_nome:
                        st.caption("Nota: Estas são modalidades de crédito emergencial com juros elevados.")
                else:
                    st.write("Dados de ranking insuficientes para gerar insights de modalidade.")

        else:
            st.warning("Dados de Inadimplência insuficientes para calcular variações.")

except Exception as e:

    st.error(f"Erro geral no processamento do painel: {e}")
