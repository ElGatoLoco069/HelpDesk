# Camada de relatórios para Power BI

## Objetivo

Esta camada oferece dados estáveis e amigáveis para análise sem conectar o Power BI às tabelas transacionais brutas. A implementação oficial é PostgreSQL. O SQLite possui um fallback para desenvolvimento e validação local.

As views não expõem descrição do chamado, chat, relatórios técnicos, anexos, e-mail, telefone, senhas ou tokens. Nomes, identificadores de usuários e departamento continuam sendo dados pessoais e devem ter acesso restrito.

## Instalação e atualização

Depois de publicar o código, execute no mesmo ambiente/configuração de banco da aplicação:

```powershell
python manage.py migrate
python manage.py create_report_views
```

O comando escolhe `database/reports_views.sql` no PostgreSQL e `database/reports_views_sqlite.sql` no SQLite. Ele não é executado na inicialização da aplicação. Reexecute-o após mudanças nos scripts de views.

Os campos `closed_at`, `first_response_at`, `assigned_at`, `cancelled_at` e `reopened_at` são opcionais. A migration não inventa datas para chamados históricos. Novas transições passam a preenchê-los sem sobrescrever o primeiro marco registrado.

## Catálogo de views

### `vw_relatorio_chamados_geral`

Fonte recomendada para análises detalhadas. Uma linha por chamado:

- identificação: `chamado_id`, `numero_chamado`, `titulo`;
- datas: `data_abertura`, `data_atualizacao`, `data_fechamento`, `data_primeira_resposta`, `data_atribuicao`, `data_cancelamento`, `data_reabertura`;
- classificações: `status`, `prioridade`, `categoria`, `setor_unidade`;
- pessoas: `solicitante_id`, `solicitante_nome`, `tecnico_id`, `tecnico_nome`;
- métricas: `tempo_resolucao_horas`, `tempo_primeira_resposta_horas`;
- indicadores: `chamado_concluido`, `chamado_cancelado`, `chamado_em_aberto`.

O campo `titulo` corresponde à subcategoria cadastrada no sistema. Os tempos são horas corridas, não horas úteis.

### Views agregadas

- `vw_chamados_por_status`: totais abertos, concluídos e cancelados por status.
- `vw_chamados_por_tecnico`: volume e tempos médios por técnico.
- `vw_chamados_por_categoria`: volume e tempo médio de resolução por categoria.
- `vw_chamados_por_prioridade`: volume e tempo médio de resolução por prioridade.
- `vw_chamados_abertos_fechados_mes`: eventos de abertura, fechamento e cancelamento por ano/mês.
- `vw_chamados_abertos_dia`: quantidade de chamados abertos em cada dia, com ano, mês, semana e dia da semana.
- `vw_chamados_abertos_semana`: quantidade de chamados abertos por semana, com datas inicial e final da semana.
- `vw_produtividade_tecnicos`: atribuídos, concluídos, em andamento e tempos médios.
- `vw_chamados_em_atraso`: chamados ainda abertos, prazo calculado e indicador de atraso.
- `dim_calendario`: calendário diário de 01/01/2024 a 31/12/2035.

## SLA

O sistema já possui `Priority.first_interaction_limit` e `Priority.estimated_service_time`. A view de atraso considera `estimated_service_time` em minutos a partir da abertura:

`prazo_sla = data_abertura + estimated_service_time minutos`

Confirme com a área de negócio se os valores cadastrados realmente representam minutos corridos. Para SLA em horas úteis, feriados ou pausas, será necessária uma regra adicional; a `dim_calendario` atual identifica fins de semana, mas não feriados. `first_interaction_limit` pode ser comparado à métrica de primeira resposta em um indicador futuro.

## Conexão do Power BI ao PostgreSQL

1. Crie no PostgreSQL um usuário exclusivo e somente leitura para BI.
2. No Power BI Desktop, use **Obter dados > Banco de dados PostgreSQL**.
3. Informe servidor/porta e banco, autentique com o usuário de BI e selecione apenas as views públicas listadas acima.
4. Prefira o modo **Importar** para desempenho e agende atualização no Power BI Service. Use DirectQuery apenas quando a necessidade de atualização quase em tempo real justificar o custo no banco.
5. Se o PostgreSQL não estiver acessível pela nuvem, configure um gateway de dados na rede do servidor.

Exemplo de permissões, a ser adaptado pelo DBA:

```sql
CREATE ROLE powerbi_reader LOGIN PASSWORD 'use-um-segredo-forte';
GRANT CONNECT ON DATABASE helpdesk TO powerbi_reader;
GRANT USAGE ON SCHEMA public TO powerbi_reader;
GRANT SELECT ON vw_relatorio_chamados_geral,
    vw_chamados_por_status,
    vw_chamados_por_tecnico,
    vw_chamados_por_categoria,
    vw_chamados_por_prioridade,
    vw_chamados_abertos_fechados_mes,
    vw_chamados_abertos_dia,
    vw_chamados_abertos_semana,
    vw_produtividade_tecnicos,
    vw_chamados_em_atraso,
    dim_calendario
TO powerbi_reader;
```

Não conceda `SELECT` nas tabelas brutas ao usuário do Power BI.

## Modelo sugerido no Power BI

Use `vw_relatorio_chamados_geral` como fato central e `dim_calendario` como dimensão de data:

- relação ativa: `dim_calendario[data]` para a data, sem hora, derivada de `data_abertura`;
- relações inativas opcionais: calendário para `data_fechamento`, `data_cancelamento` e `data_primeira_resposta`, ativadas nas medidas quando necessário;
- use `tecnico_id` e `solicitante_id` como chaves, evitando relacionar por nomes;
- não relacione simultaneamente as views agregadas à fato. Use-as como fontes de páginas simples ou, preferencialmente, calcule medidas sobre a fato para evitar dupla contagem.

No Power Query, crie colunas do tipo **Data** a partir dos timestamps antes de relacioná-los ao calendário. O banco e o Django armazenam timestamps com suporte a fuso; valide a conversão para `America/Sao_Paulo` no refresh do Power BI.

## Indicadores disponíveis

- total aberto, concluído, em andamento e cancelado;
- chamados por status, categoria, prioridade, técnico e setor/unidade;
- abertos, concluídos e cancelados por mês;
- chamados abertos por dia e por semana;
- tempo médio de resolução e de primeira resposta;
- ranking de técnicos por chamados concluídos;
- ranking de categorias e setores com maior demanda;
- produtividade por técnico;
- chamados vencidos e horas em aberto;
- percentual atendido dentro do SLA de resolução;
- satisfação média, caso futuramente seja criada uma view específica e governada para esse dado.

## Validação operacional

No PostgreSQL, valide após aplicar as views:

```sql
SELECT COUNT(*) FROM vw_relatorio_chamados_geral;
SELECT * FROM vw_chamados_por_status ORDER BY total_chamados DESC;
SELECT * FROM vw_chamados_em_atraso WHERE atrasado = TRUE;
SELECT MIN(data), MAX(data), COUNT(*) FROM dim_calendario;
```

Compare a primeira contagem com `SELECT COUNT(*) FROM ticket_ticket`. Verifique manualmente um chamado concluído, um cancelado, um atribuído e um com resposta técnica.

## Segurança, desempenho e manutenção

- Restrinja acesso a nomes e departamentos conforme LGPD e política interna.
- Não publique a view detalhada em workspaces abertos a toda a organização.
- Use segurança em nível de linha no Power BI se equipes só puderem ver seus próprios setores.
- As FKs de status, prioridade, subcategoria, solicitante e técnico já são indexadas pelo Django. A migration de relatórios adiciona índices a `created_at` e às cinco datas de ciclo de vida.
- Para grande volume, configure atualização incremental por `data_atualizacao` ou `data_abertura` e monitore os planos com `EXPLAIN (ANALYZE, BUFFERS)`.
- Se novos nomes de status conclusivo/cancelado forem cadastrados, atualize os conjuntos centralizados em `ticket/models.py` e os dois scripts SQL no mesmo deploy.
