-- Camada de relatorios para PostgreSQL.
-- Nao expoe descricao, mensagens, anexos, e-mail, telefone ou credenciais.

CREATE OR REPLACE VIEW vw_relatorio_chamados_geral AS
SELECT
    t.id AS chamado_id,
    t.hash AS numero_chamado,
    sc.name AS titulo,
    t.created_at AS data_abertura,
    t.updated_at AS data_atualizacao,
    t.closed_at AS data_fechamento,
    t.first_response_at AS data_primeira_resposta,
    t.assigned_at AS data_atribuicao,
    t.cancelled_at AS data_cancelamento,
    t.reopened_at AS data_reabertura,
    st.name AS status,
    p.name AS prioridade,
    c.name AS categoria,
    t.created_by_id AS solicitante_id,
    COALESCE(NULLIF(TRIM(CONCAT_WS(' ', requester.first_name, requester.last_name)), ''), requester.username) AS solicitante_nome,
    t.assigned_to_id AS tecnico_id,
    CASE
        WHEN technician.id IS NULL THEN NULL
        ELSE COALESCE(NULLIF(TRIM(CONCAT_WS(' ', technician.first_name, technician.last_name)), ''), technician.username)
    END AS tecnico_nome,
    requester_profile.departamento AS setor_unidade,
    CASE
        WHEN t.closed_at IS NULL THEN NULL
        ELSE ROUND((
            GREATEST(
                EXTRACT(EPOCH FROM (t.closed_at - t.created_at))
                - t.resolution_paused_seconds
                - CASE
                    WHEN t.resolution_paused_at IS NULL THEN 0
                    ELSE GREATEST(EXTRACT(EPOCH FROM (t.closed_at - t.resolution_paused_at)), 0)
                END,
                0
            ) / 3600.0
        )::numeric, 2)
    END AS tempo_resolucao_horas,
    ROUND((EXTRACT(EPOCH FROM (t.first_response_at - t.created_at)) / 3600.0)::numeric, 2) AS tempo_primeira_resposta_horas,
    (LOWER(TRIM(st.name)) IN ('concluido', 'concluído', 'concluida', 'concluída', 'resolvido', 'resolvida', 'fechado', 'fechada', 'finalizado', 'finalizada')) AS chamado_concluido,
    (LOWER(TRIM(st.name)) IN ('cancelado', 'cancelada')) AS chamado_cancelado,
    (LOWER(TRIM(st.name)) NOT IN ('concluido', 'concluído', 'concluida', 'concluída', 'resolvido', 'resolvida', 'fechado', 'fechada', 'finalizado', 'finalizada', 'cancelado', 'cancelada')) AS chamado_em_aberto,
    (t.resolution_paused_at IS NOT NULL) AS resolucao_pausada,
    ROUND((
        (
            t.resolution_paused_seconds
            + CASE
                WHEN t.resolution_paused_at IS NULL THEN 0
                ELSE GREATEST(EXTRACT(EPOCH FROM (
                    COALESCE(t.closed_at, t.cancelled_at, CURRENT_TIMESTAMP) - t.resolution_paused_at
                )), 0)
            END
        ) / 3600.0
    )::numeric, 2) AS tempo_pausado_resolucao_horas,
    CASE
        WHEN t.closed_at IS NULL THEN NULL
        ELSE ROUND((EXTRACT(EPOCH FROM (t.closed_at - t.created_at)) / 3600.0)::numeric, 2)
    END AS tempo_resolucao_corrida_horas,
    t.resolution_paused_at AS data_inicio_pausa_resolucao,
    t.resolution_paused_seconds AS segundos_resolucao_pausada_acumulados,
    t.satisfaction_rating AS nota_atendimento,
    t.evaluated_at AS data_avaliacao,
    (t.satisfaction_rating IS NOT NULL) AS atendimento_avaliado
FROM ticket_ticket t
JOIN ticket_ticket_status st ON st.id = t.status_id
JOIN registers_priority p ON p.id = t.priority_id
JOIN registers_subcategory sc ON sc.id = t.title_id
JOIN registers_category c ON c.id = sc.category_id
JOIN auth_user requester ON requester.id = t.created_by_id
LEFT JOIN accounts_profile requester_profile ON requester_profile.user_id = requester.id
LEFT JOIN auth_user technician ON technician.id = t.assigned_to_id;

CREATE OR REPLACE VIEW vw_chamados_por_status AS
SELECT
    status,
    COUNT(*) AS total_chamados,
    COUNT(*) FILTER (WHERE chamado_em_aberto) AS chamados_abertos,
    COUNT(*) FILTER (WHERE chamado_concluido) AS chamados_concluidos,
    COUNT(*) FILTER (WHERE chamado_cancelado) AS chamados_cancelados
FROM vw_relatorio_chamados_geral
GROUP BY status;

CREATE OR REPLACE VIEW vw_chamados_por_tecnico AS
SELECT
    tecnico_id,
    tecnico_nome,
    COUNT(*) AS total_chamados,
    COUNT(*) FILTER (WHERE chamado_concluido) AS chamados_concluidos,
    COUNT(*) FILTER (WHERE chamado_em_aberto) AS chamados_em_aberto,
    ROUND(AVG(tempo_resolucao_horas) FILTER (WHERE chamado_concluido), 2) AS tempo_medio_resolucao_horas,
    ROUND(AVG(tempo_primeira_resposta_horas), 2) AS tempo_medio_primeira_resposta_horas,
    COUNT(*) FILTER (WHERE nota_atendimento IS NOT NULL) AS total_avaliacoes,
    ROUND(AVG(nota_atendimento) FILTER (WHERE nota_atendimento IS NOT NULL), 2) AS nota_media
FROM vw_relatorio_chamados_geral
WHERE tecnico_id IS NOT NULL
GROUP BY tecnico_id, tecnico_nome;

CREATE OR REPLACE VIEW vw_chamados_por_categoria AS
SELECT
    categoria,
    COUNT(*) AS total_chamados,
    COUNT(*) FILTER (WHERE chamado_concluido) AS chamados_concluidos,
    COUNT(*) FILTER (WHERE chamado_em_aberto) AS chamados_em_aberto,
    ROUND(AVG(tempo_resolucao_horas) FILTER (WHERE chamado_concluido), 2) AS tempo_medio_resolucao_horas
FROM vw_relatorio_chamados_geral
GROUP BY categoria;

CREATE OR REPLACE VIEW vw_chamados_por_prioridade AS
SELECT
    prioridade,
    COUNT(*) AS total_chamados,
    COUNT(*) FILTER (WHERE chamado_concluido) AS chamados_concluidos,
    COUNT(*) FILTER (WHERE chamado_em_aberto) AS chamados_em_aberto,
    ROUND(AVG(tempo_resolucao_horas) FILTER (WHERE chamado_concluido), 2) AS tempo_medio_resolucao_horas
FROM vw_relatorio_chamados_geral
GROUP BY prioridade;

CREATE OR REPLACE VIEW vw_chamados_abertos_fechados_mes AS
WITH eventos AS (
    SELECT DATE_TRUNC('month', data_abertura)::date AS referencia, 1 AS abertos, 0 AS fechados, 0 AS cancelados
    FROM vw_relatorio_chamados_geral
    UNION ALL
    SELECT DATE_TRUNC('month', data_fechamento)::date, 0, 1, 0
    FROM vw_relatorio_chamados_geral
    WHERE data_fechamento IS NOT NULL
    UNION ALL
    SELECT DATE_TRUNC('month', data_cancelamento)::date, 0, 0, 1
    FROM vw_relatorio_chamados_geral
    WHERE data_cancelamento IS NOT NULL
)
SELECT
    EXTRACT(YEAR FROM referencia)::integer AS ano,
    EXTRACT(MONTH FROM referencia)::integer AS mes,
    SUM(abertos) AS total_abertos,
    SUM(fechados) AS total_fechados,
    SUM(cancelados) AS total_cancelados
FROM eventos
GROUP BY referencia
ORDER BY referencia;

CREATE OR REPLACE VIEW vw_chamados_abertos_dia AS
SELECT
    data_abertura::date AS data,
    EXTRACT(YEAR FROM data_abertura)::integer AS ano,
    EXTRACT(MONTH FROM data_abertura)::integer AS mes,
    EXTRACT(WEEK FROM data_abertura)::integer AS semana,
    EXTRACT(ISODOW FROM data_abertura)::integer AS dia_semana,
    COUNT(*) AS total_abertos
FROM vw_relatorio_chamados_geral
GROUP BY
    data_abertura::date,
    EXTRACT(YEAR FROM data_abertura),
    EXTRACT(MONTH FROM data_abertura),
    EXTRACT(WEEK FROM data_abertura),
    EXTRACT(ISODOW FROM data_abertura)
ORDER BY data;

CREATE OR REPLACE VIEW vw_chamados_abertos_semana AS
SELECT
    EXTRACT(ISOYEAR FROM data_abertura)::integer AS ano,
    EXTRACT(WEEK FROM data_abertura)::integer AS semana,
    DATE_TRUNC('week', data_abertura)::date AS inicio_semana,
    (DATE_TRUNC('week', data_abertura)::date + 6) AS fim_semana,
    COUNT(*) AS total_abertos
FROM vw_relatorio_chamados_geral
GROUP BY
    EXTRACT(ISOYEAR FROM data_abertura),
    EXTRACT(WEEK FROM data_abertura),
    DATE_TRUNC('week', data_abertura)::date
ORDER BY inicio_semana;

CREATE OR REPLACE VIEW vw_produtividade_tecnicos AS
SELECT
    tecnico_id,
    tecnico_nome,
    COUNT(*) AS total_atribuidos,
    COUNT(*) FILTER (WHERE chamado_concluido) AS total_concluidos,
    COUNT(*) FILTER (WHERE chamado_em_aberto) AS total_em_andamento,
    ROUND(AVG(tempo_resolucao_horas) FILTER (WHERE chamado_concluido), 2) AS tempo_medio_resolucao_horas,
    ROUND(AVG(tempo_primeira_resposta_horas), 2) AS tempo_medio_primeira_resposta_horas,
    COUNT(*) FILTER (WHERE nota_atendimento IS NOT NULL) AS total_avaliacoes,
    ROUND(AVG(nota_atendimento) FILTER (WHERE nota_atendimento IS NOT NULL), 2) AS nota_media
FROM vw_relatorio_chamados_geral
WHERE tecnico_id IS NOT NULL
GROUP BY tecnico_id, tecnico_nome;

CREATE OR REPLACE VIEW vw_avaliacoes_tecnicos AS
SELECT
    t.id AS chamado_id,
    t.hash AS numero_chamado,
    t.evaluated_at AS data_avaliacao,
    t.closed_at AS data_fechamento,
    t.satisfaction_rating AS nota,
    (t.satisfaction_comment LIKE 'Avaliacao automatica:%') AS avaliacao_automatica,
    t.assigned_to_id AS tecnico_id,
    CASE
        WHEN technician.id IS NULL THEN NULL
        ELSE COALESCE(NULLIF(TRIM(CONCAT_WS(' ', technician.first_name, technician.last_name)), ''), technician.username)
    END AS tecnico_nome,
    p.name AS prioridade,
    c.name AS categoria,
    requester_profile.departamento AS setor_unidade
FROM ticket_ticket t
JOIN registers_priority p ON p.id = t.priority_id
JOIN registers_subcategory sc ON sc.id = t.title_id
JOIN registers_category c ON c.id = sc.category_id
JOIN auth_user requester ON requester.id = t.created_by_id
LEFT JOIN accounts_profile requester_profile ON requester_profile.user_id = requester.id
LEFT JOIN auth_user technician ON technician.id = t.assigned_to_id
WHERE t.satisfaction_rating IS NOT NULL
  AND t.assigned_to_id IS NOT NULL;

CREATE OR REPLACE VIEW vw_notas_tecnicos AS
SELECT
    tecnico_id,
    tecnico_nome,
    COUNT(*) AS total_avaliacoes,
    ROUND(AVG(nota)::numeric, 2) AS nota_media,
    MIN(nota) AS menor_nota,
    MAX(nota) AS maior_nota,
    COUNT(*) FILTER (WHERE nota = 1) AS notas_1,
    COUNT(*) FILTER (WHERE nota = 2) AS notas_2,
    COUNT(*) FILTER (WHERE nota = 3) AS notas_3,
    COUNT(*) FILTER (WHERE nota = 4) AS notas_4,
    COUNT(*) FILTER (WHERE nota = 5) AS notas_5,
    COUNT(*) FILTER (WHERE nota >= 4) AS notas_4_5,
    ROUND(((COUNT(*) FILTER (WHERE nota >= 4) * 100.0) / NULLIF(COUNT(*), 0))::numeric, 2) AS percentual_notas_4_5,
    COUNT(*) FILTER (WHERE avaliacao_automatica) AS avaliacoes_automaticas,
    MAX(data_avaliacao) AS ultima_avaliacao
FROM vw_avaliacoes_tecnicos
GROUP BY tecnico_id, tecnico_nome;

CREATE OR REPLACE VIEW vw_chamados_em_atraso AS
WITH chamados AS (
    SELECT
        t.id AS chamado_id,
        t.hash AS numero_chamado,
        sc.name AS titulo,
        st.name AS status,
        p.name AS prioridade,
        p.estimated_service_time AS prazo_sla_minutos,
        c.name AS categoria,
        CASE
            WHEN technician.id IS NULL THEN NULL
            ELSE COALESCE(NULLIF(TRIM(CONCAT_WS(' ', technician.first_name, technician.last_name)), ''), technician.username)
        END AS tecnico_nome,
        t.created_at AS data_abertura,
        (
            t.resolution_paused_seconds
            + CASE
                WHEN t.resolution_paused_at IS NULL THEN 0
                ELSE GREATEST(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - t.resolution_paused_at)), 0)
            END
        ) AS pausa_resolucao_segundos
    FROM ticket_ticket t
    JOIN ticket_ticket_status st ON st.id = t.status_id
    JOIN registers_priority p ON p.id = t.priority_id
    JOIN registers_subcategory sc ON sc.id = t.title_id
    JOIN registers_category c ON c.id = sc.category_id
    LEFT JOIN auth_user technician ON technician.id = t.assigned_to_id
    WHERE LOWER(TRIM(st.name)) NOT IN ('concluido', 'concluído', 'concluida', 'concluída', 'resolvido', 'resolvida', 'fechado', 'fechada', 'finalizado', 'finalizada', 'cancelado', 'cancelada')
)
SELECT
    chamado_id,
    numero_chamado,
    titulo,
    status,
    prioridade,
    categoria,
    tecnico_nome,
    data_abertura,
    data_abertura
        + MAKE_INTERVAL(mins => prazo_sla_minutos)
        + (pausa_resolucao_segundos::double precision * INTERVAL '1 second') AS prazo_sla,
    ROUND((
        GREATEST(
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - data_abertura)) - pausa_resolucao_segundos,
            0
        ) / 3600.0
    )::numeric, 2) AS horas_em_aberto,
    (
        GREATEST(
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - data_abertura)) - pausa_resolucao_segundos,
            0
        ) > (prazo_sla_minutos * 60)
    ) AS atrasado
FROM chamados;

CREATE OR REPLACE VIEW dim_calendario AS
SELECT
    dia::date AS data,
    EXTRACT(YEAR FROM dia)::integer AS ano,
    EXTRACT(MONTH FROM dia)::integer AS mes,
    CASE EXTRACT(MONTH FROM dia)::integer
        WHEN 1 THEN 'Janeiro' WHEN 2 THEN 'Fevereiro' WHEN 3 THEN 'Março'
        WHEN 4 THEN 'Abril' WHEN 5 THEN 'Maio' WHEN 6 THEN 'Junho'
        WHEN 7 THEN 'Julho' WHEN 8 THEN 'Agosto' WHEN 9 THEN 'Setembro'
        WHEN 10 THEN 'Outubro' WHEN 11 THEN 'Novembro' ELSE 'Dezembro'
    END AS nome_mes,
    EXTRACT(QUARTER FROM dia)::integer AS trimestre,
    EXTRACT(WEEK FROM dia)::integer AS semana,
    EXTRACT(DAY FROM dia)::integer AS dia,
    EXTRACT(ISODOW FROM dia)::integer AS dia_semana,
    CASE EXTRACT(ISODOW FROM dia)::integer
        WHEN 1 THEN 'Segunda-feira' WHEN 2 THEN 'Terça-feira' WHEN 3 THEN 'Quarta-feira'
        WHEN 4 THEN 'Quinta-feira' WHEN 5 THEN 'Sexta-feira' WHEN 6 THEN 'Sábado'
        ELSE 'Domingo'
    END AS nome_dia_semana,
    (EXTRACT(ISODOW FROM dia)::integer IN (6, 7)) AS eh_final_de_semana
FROM GENERATE_SERIES(DATE '2024-01-01', DATE '2035-12-31', INTERVAL '1 day') AS calendario(dia);
