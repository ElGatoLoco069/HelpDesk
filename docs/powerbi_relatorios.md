# Camada de relatorios para Power BI

## Objetivo

Esta camada oferece dados estaveis e amigaveis para analise sem conectar o Power BI as tabelas transacionais brutas. A implementacao oficial e PostgreSQL. O SQLite possui um fallback para desenvolvimento e validacao local.

As views nao expoem descricao do chamado, chat, relatorios tecnicos, anexos, e-mail, telefone, senhas ou tokens. Nomes, identificadores de usuarios e departamento continuam sendo dados pessoais e devem ter acesso restrito.

## Instalacao e atualizacao

Depois de publicar o codigo, execute no mesmo ambiente/configuracao de banco da aplicacao:

```powershell
python manage.py migrate
python manage.py create_report_views
```

O comando escolhe `database/reports_views.sql` no PostgreSQL e `database/reports_views_sqlite.sql` no SQLite. Ele nao e executado na inicializacao da aplicacao. Reexecute-o apos mudancas nos scripts de views.

Os campos `closed_at`, `first_response_at`, `assigned_at`, `cancelled_at`, `reopened_at`, `resolution_paused_at` e `resolution_paused_seconds` podem ficar vazios em chamados historicos. A migration nao inventa datas antigas; chamados que ja estiverem em status pausado passam a pausar a contagem a partir da aplicacao da migration.

## Catalogo de views

### `vw_relatorio_chamados_geral`

Fonte recomendada para analises detalhadas. Uma linha por chamado:

- identificacao: `chamado_id`, `numero_chamado`, `titulo`;
- datas: `data_abertura`, `data_atualizacao`, `data_fechamento`, `data_primeira_resposta`, `data_atribuicao`, `data_cancelamento`, `data_reabertura`;
- classificacoes: `status`, `prioridade`, `categoria`, `setor_unidade`;
- pessoas: `solicitante_id`, `solicitante_nome`, `tecnico_id`, `tecnico_nome`;
- metricas: `tempo_resolucao_horas`, `tempo_primeira_resposta_horas`, `tempo_pausado_resolucao_horas`, `tempo_resolucao_corrida_horas`;
- indicadores: `chamado_concluido`, `chamado_cancelado`, `chamado_em_aberto`, `resolucao_pausada`, `atendimento_avaliado`;
- avaliacao: `nota_atendimento`, `data_avaliacao`.

O campo `titulo` corresponde a subcategoria cadastrada no sistema. `tempo_resolucao_horas` desconta pausas de resolucao; `tempo_resolucao_corrida_horas` mantem o tempo bruto entre abertura e fechamento.

### Views agregadas

- `vw_chamados_por_status`: totais abertos, concluidos e cancelados por status.
- `vw_chamados_por_tecnico`: volume, tempos medios e nota media por tecnico.
- `vw_chamados_por_categoria`: volume e tempo medio de resolucao por categoria.
- `vw_chamados_por_prioridade`: volume e tempo medio de resolucao por prioridade.
- `vw_chamados_abertos_fechados_mes`: eventos de abertura, fechamento e cancelamento por ano/mes.
- `vw_chamados_abertos_dia`: quantidade de chamados abertos em cada dia, com ano, mes, semana e dia da semana.
- `vw_chamados_abertos_semana`: quantidade de chamados abertos por semana, com datas inicial e final da semana.
- `vw_produtividade_tecnicos`: atribuidos, concluidos, em andamento, tempos medios e nota media.
- `vw_avaliacoes_tecnicos`: avaliacoes detalhadas por chamado avaliado, sem expor comentarios textuais.
- `vw_notas_tecnicos`: total de avaliacoes, nota media e distribuicao de notas por tecnico.
- `vw_chamados_em_atraso`: chamados ainda abertos, prazo calculado e indicador de atraso.
- `dim_calendario`: calendario diario de 01/01/2024 a 31/12/2035.

## SLA

O sistema ja possui `Priority.first_interaction_limit` e `Priority.estimated_service_time`. A view de atraso considera `estimated_service_time` em minutos a partir da abertura, prorrogando o prazo pelo tempo acumulado em status pausados:

`prazo_sla = data_abertura + estimated_service_time minutos + tempo_pausado`

Status como `Acao do Cliente`, `Aguardando Cliente`, `Aguardando Solicitante`, `Aguardando Fornecedor` e `Proposta de Solucao` pausam a contagem de resolucao. A `dim_calendario` atual identifica fins de semana, mas nao feriados; para SLA em horas uteis sera necessaria uma regra adicional.

## Conexao do Power BI ao PostgreSQL

1. Crie no PostgreSQL um usuario exclusivo e somente leitura para BI.
2. No Power BI Desktop, use **Obter dados > Banco de dados PostgreSQL**.
3. Informe servidor/porta e banco, autentique com o usuario de BI e selecione apenas as views publicas listadas acima.
4. Prefira o modo **Importar** para desempenho e agende atualizacao no Power BI Service. Use DirectQuery apenas quando a necessidade de atualizacao quase em tempo real justificar o custo no banco.
5. Se o PostgreSQL nao estiver acessivel pela nuvem, configure um gateway de dados na rede do servidor.

Exemplo de permissoes, a ser adaptado pelo DBA:

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
    vw_avaliacoes_tecnicos,
    vw_notas_tecnicos,
    vw_chamados_em_atraso,
    dim_calendario
TO powerbi_reader;
```

Nao conceda `SELECT` nas tabelas brutas ao usuario do Power BI.

## Modelo sugerido no Power BI

Use `vw_relatorio_chamados_geral` como fato central e `dim_calendario` como dimensao de data:

- relacao ativa: `dim_calendario[data]` para a data, sem hora, derivada de `data_abertura`;
- relacoes inativas opcionais: calendario para `data_fechamento`, `data_cancelamento`, `data_primeira_resposta` e `data_avaliacao`, ativadas nas medidas quando necessario;
- use `tecnico_id` e `solicitante_id` como chaves, evitando relacionar por nomes;
- para dashboards de notas, use `vw_notas_tecnicos` em paginas agregadas e `vw_avaliacoes_tecnicos` quando precisar detalhar por chamado;
- nao relacione simultaneamente as views agregadas a fato. Use-as como fontes de paginas simples ou calcule medidas sobre a fato para evitar dupla contagem.

No Power Query, crie colunas do tipo **Data** a partir dos timestamps antes de relaciona-los ao calendario. O banco e o Django armazenam timestamps com suporte a fuso; valide a conversao para `America/Sao_Paulo` no refresh do Power BI.

## Indicadores disponiveis

- total aberto, concluido, em andamento e cancelado;
- chamados por status, categoria, prioridade, tecnico e setor/unidade;
- abertos, concluidos e cancelados por mes;
- chamados abertos por dia e por semana;
- tempo medio de resolucao liquido, tempo corrido, tempo pausado e primeira resposta;
- ranking de tecnicos por chamados concluidos;
- ranking de categorias e setores com maior demanda;
- produtividade por tecnico;
- chamados vencidos e horas em aberto;
- percentual atendido dentro do SLA de resolucao;
- satisfacao media, distribuicao de notas e avaliacoes automaticas por tecnico.

## Validacao operacional

No PostgreSQL, valide apos aplicar as views:

```sql
SELECT COUNT(*) FROM vw_relatorio_chamados_geral;
SELECT * FROM vw_chamados_por_status ORDER BY total_chamados DESC;
SELECT * FROM vw_chamados_em_atraso WHERE atrasado = TRUE;
SELECT * FROM vw_notas_tecnicos ORDER BY nota_media DESC;
SELECT MIN(data), MAX(data), COUNT(*) FROM dim_calendario;
```

Compare a primeira contagem com `SELECT COUNT(*) FROM ticket_ticket`. Verifique manualmente um chamado concluido, um cancelado, um atribuido, um pausado e um avaliado.

## Seguranca, desempenho e manutencao

- Restrinja acesso a nomes e departamentos conforme LGPD e politica interna.
- Nao publique a view detalhada em workspaces abertos a toda a organizacao.
- Use seguranca em nivel de linha no Power BI se equipes so puderem ver seus proprios setores.
- As FKs de status, prioridade, subcategoria, solicitante e tecnico ja sao indexadas pelo Django. As datas de ciclo de vida e `resolution_paused_at` tambem possuem indice.
- Para grande volume, configure atualizacao incremental por `data_atualizacao` ou `data_abertura` e monitore os planos com `EXPLAIN (ANALYZE, BUFFERS)`.
- Se novos nomes de status conclusivo, cancelado ou pausado forem cadastrados, atualize os conjuntos centralizados em `ticket/models.py` e os dois scripts SQL no mesmo deploy.
