# \# Histórico de prompts

# 

# Registro dos prompts usados com o assistente de IA (Claude) na construção do projeto, na ordem em que ocorreram. Trechos entre aspas são resumos; o texto integral da conversa está disponível se solicitado.

# 

# \## 1. Especificação e primeira implementação (25/11/2026)

# \*\*Contexto:\*\* enunciado do projeto do módulo e link da página do projeto.

# \*\*Prompt:\*\* pedi ajuda para fazer o projeto completo (pipeline Pokémon TCG, lakehouse DuckDB/Parquet, modelo dimensional, dashboard em Streamlit e desafio da carteira).

# \*\*Resultado:\*\* repositório inicial com coletor, silver (Pydantic), gold (DuckDB), cinco perguntas, carteiras, dashboard, testes e ADRs.

# \*\*O que validei:\*\* rodei a suíte de testes na minha máquina (28 passaram) e conferi a estrutura no GitHub.

# 

# \## 2. Passo a passo guiado

# \*\*Prompt:\*\* pedi um roteiro detalhado, um passo por vez, com blocos de código separados, avançando só quando cada passo desse certo.

# \*\*Resultado:\*\* preparação de ambiente, Git, repositório no GitHub, .env, escolha da coleção, coleta, agendamento e dashboard.

# 

# \## 3. Escolha da coleção com dados reais

# \*\*Contexto:\*\* a booster box da POR custava mais de R$ 1.000 com a PTAX do dia.

# \*\*Prompt:\*\* colei a saída do script de inspeção (preços reais do TCGCSV) e pedi ajuda para escolher.

# \*\*Resultado:\*\* troquei para a PBL (ME05: Pitch Black), cuja booster box cabe nos R$ 1.000.

# \*\*Ajuste meu:\*\* conferi a lista de coleções livres no lake antes da primeira gravação.

# 

# \## 4. Correção do boletim da PTAX

# \*\*Contexto:\*\* a silver saiu com 0 cotações de câmbio e a carteira falhou.

# \*\*Prompt:\*\* colei o erro e o JSON bruto da PTAX.

# \*\*Causa encontrada:\*\* o Banco Central devolve o boletim como "Fechamento PTAX", e o código procurava "Fechamento".

# \*\*Resultado:\*\* filtro corrigido para aceitar nomes que começam com "Fechamento"; reconstruí a silver a partir do bruto, que ficou intacto.

# 

# \## 5. Agendamento no GitHub Actions

# \*\*Contexto:\*\* a primeira execução repetiu um commit antigo e regravou a silver vazia.

# \*\*Resultado:\*\* reconstruí a silver pelo meu computador e confirmei com uma execução nova, com o código atual.

# 

# \## 6. Classificação de selados (ADR 0009)

# \*\*Prompt:\*\* colei as raridades e a lista de selados da PBL.

# \*\*Resultado:\*\* pergunta 2 passou a usar só selados de varejo, sem cases nem displays.

# 

# \## 7. Dashboard com poucos dados

# \*\*Contexto:\*\* erro "Neither start nor end can be NaT" na pergunta 5 e gráficos de 1 ponto.

# \*\*Prompt:\*\* colei os prints de todas as abas.

# \*\*Resultado:\*\* cada aba mostra seu próprio erro, avisos no lugar de gráficos vazios e placar da turma tolerante a diferenças na taxa de dólar/CDI.

# 

# \## Decisões minhas, não da IA

# \- Aceitar a PBL como coleção definitiva.

# \- Aceitar a regra da carteira própria (ADR 0005) e commitar o ADR antes do primeiro cálculo oficial.

# \- Levar à mentoria o ponto em aberto sobre a cesta de raras (ADR 0003).

