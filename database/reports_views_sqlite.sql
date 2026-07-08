-- Fallback de desenvolvimento para SQLite. A camada oficial de BI e PostgreSQL.

DROP VIEW IF EXISTS vw_chamados_por_status;
DROP VIEW IF EXISTS vw_chamados_por_tecnico;
DROP VIEW IF EXISTS vw_chamados_por_categoria;
DROP VIEW IF EXISTS vw_chamados_por_prioridade;
DROP VIEW IF EXISTS vw_chamados_abertos_fechados_mes;
DROP VIEW IF EXISTS vw_chamados_abertos_dia;
DROP VIEW IF EXISTS vw_chamados_abertos_semana;
DROP VIEW IF EXISTS vw_produtividade_tecnicos;
DROP VIEW IF EXISTS vw_notas_tecnicos;
DROP VIEW IF EXISTS vw_avaliacoes_tecnicos;
DROP VIEW IF EXISTS vw_chamados_em_atraso;
DROP VIEW IF EXISTS dim_calendario;
DROP VIEW IF EXISTS vw_relatorio_chamados_geral;

CREATE VIEW vw_relatorio_chamados_geral AS
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
    COALESCE(NULLIF(TRIM(COALESCE(requester.first_name, '') || ' ' || COALESCE(requester.last_name, '')), ''), requester.username) AS solicitante_nome,
    t.assigned_to_id AS tecnico_id,
    CASE
        WHEN technician.id IS NULL THEN NULL
        ELSE COALESCE(NULLIF(TRIM(COALESCE(technician.first_name, '') || ' ' || COALESCE(technician.last_name, '')), ''), technician.username)
    END AS tecnico_nome,
    requester_profile.departamento AS setor_unidade,
    CASE
        WHEN t.closed_at IS NULL THEN NULL
        ELSE ROUND(
            MAX(
                ((JULIANDAY(t.closed_at) - JULIANDAY(t.created_at)) * 86400.0)
                - t.resolution_paused_seconds
                - CASE
                    WHEN t.resolution_paused_at IS NULL THEN 0
                    ELSE MAX((JULIANDAY(t.closed_at) - JULIANDAY(t.resolution_paused_at)) * 86400.0, 0)
                END,
                0
            ) / 3600.0,
            2
        )
    END AS tempo_resolucao_horas,
    ROUND((JULIANDAY(t.first_response_at) - JULIANDAY(t.created_at)) * 24.0, 2) AS tempo_primeira_resposta_horas,
    CASE WHEN LOWER(TRIM(st.name)) IN ('concluido', 'concluído', 'concluida', 'concluída', 'resolvido', 'resolvida', 'fechado', 'fechada', 'finalizado', 'finalizada') THEN 1 ELSE 0 END AS chamado_concluido,
    CASE WHEN LOWER(TRIM(st.name)) IN ('cancelado', 'cancelada') THEN 1 ELSE 0 END AS chamado_cancelado,
    CASE WHEN LOWER(TRIM(st.name)) NOT IN ('concluido', 'concluído', 'concluida', 'concluída', 'resolvido', 'resolvida', 'fechado', 'fechada', 'finalizado', 'finalizada', 'cancelado', 'cancelada') THEN 1 ELSE 0 END AS chamado_em_aberto,
    CASE WHEN t.resolution_paused_at IS NOT NULL THEN 1 ELSE 0 END AS resolucao_pausada,
    ROUND(
        (
            t.resolution_paused_seconds
            + CASE
                WHEN t.resolution_paused_at IS NULL THEN 0
                ELSE MAX(
                    (JULIANDAY(COALESCE(t.closed_at, t.cancelled_at, CURRENT_TIMESTAMP)) - JULIANDAY(t.resolution_paused_at)) * 86400.0,
                    0
                )
            END
        ) / 3600.0,
        2
    ) AS tempo_pausado_resolucao_horas,
    CASE
        WHEN t.closed_at IS NULL THEN NULL
        ELSE ROUND((JULIANDAY(t.closed_at) - JULIANDAY(t.created_at)) * 24.0, 2)
    END AS tempo_resolucao_corrida_horas,
    t.resolution_paused_at AS data_inicio_pausa_resolucao,
    t.resolution_paused_seconds AS segundos_resolucao_pausada_acumulados,
    t.satisfaction_rating AS nota_atendimento,
    t.evaluated_at AS data_avaliacao,
    CASE WHEN t.satisfaction_rating IS NOT NULL THEN 1 ELSE 0 END AS atendimento_avaliado
FROM ticket_ticket t
JOIN ticket_ticket_status st ON st.id = t.status_id
JOIN registers_priority p ON p.id = t.priority_id
JOIN registers_subcategory sc ON sc.id = t.title_id
JOIN registers_category c ON c.id = sc.category_id
JOIN auth_user requester ON requester.id = t.created_by_id
LEFT JOIN accounts_profile requester_profile ON requester_profile.user_id = requester.id
LEFT JOIN auth_user technician ON technician.id = t.assigned_to_id;

CREATE VIEW vw_chamados_por_status AS
SELECT
    status,
    COUNT(*) AS total_chamados,
    SUM(chamado_em_aberto) AS chamados_abertos,
    SUM(chamado_concluido) AS chamados_concluidos,
    SUM(chamado_cancelado) AS chamados_cancelados
FROM vw_relatorio_chamados_geral
GROUP BY status;

CREATE VIEW vw_chamados_por_tecnico AS
SELECT
    tecnico_id,
    tecnico_nome,
    COUNT(*) AS total_chamados,
    SUM(chamado_concluido) AS chamados_concluidos,
    SUM(chamado_em_aberto) AS chamados_em_aberto,
    ROUND(AVG(CASE WHEN chamado_concluido = 1 THEN tempo_resolucao_horas END), 2) AS tempo_medio_resolucao_horas,
    ROUND(AVG(tempo_primeira_resposta_horas), 2) AS tempo_medio_primeira_resposta_horas,
    SUM(CASE WHEN nota_atendimento IS NOT NULL THEN 1 ELSE 0 END) AS total_avaliacoes,
    ROUND(AVG(nota_atendimento), 2) AS nota_media
FROM vw_relatorio_chamados_geral
WHERE tecnico_id IS NOT NULL
GROUP BY tecnico_id, tecnico_nome;

CREATE VIEW vw_chamados_por_categoria AS
SELECT
    categoria,
    COUNT(*) AS total_chamados,
    SUM(chamado_concluido) AS chamados_concluidos,
    SUM(chamado_em_aberto) AS chamados_em_aberto,
    ROUND(AVG(CASE WHEN chamado_concluido = 1 THEN tempo_resolucao_horas END), 2) AS tempo_medio_resolucao_horas
FROM vw_relatorio_chamados_geral
GROUP BY categoria;

CREATE VIEW vw_chamados_por_prioridade AS
SELECT
    prioridade,
    COUNT(*) AS total_chamados,
    SUM(chamado_concluido) AS chamados_concluidos,
    SUM(chamado_em_aberto) AS chamados_em_aberto,
    ROUND(AVG(CASE WHEN chamado_concluido = 1 THEN tempo_resolucao_horas END), 2) AS tempo_medio_resolucao_horas
FROM vw_relatorio_chamados_geral
GROUP BY prioridade;

CREATE VIEW vw_chamados_abertos_fechados_mes AS
WITH eventos AS (
    SELECT STRFTIME('%Y-%m-01', data_abertura) AS referencia, 1 AS abertos, 0 AS fechados, 0 AS cancelados
    FROM vw_relatorio_chamados_geral
    UNION ALL
    SELECT STRFTIME('%Y-%m-01', data_fechamento), 0, 1, 0
    FROM vw_relatorio_chamados_geral
    WHERE data_fechamento IS NOT NULL
    UNION ALL
    SELECT STRFTIME('%Y-%m-01', data_cancelamento), 0, 0, 1
    FROM vw_relatorio_chamados_geral
    WHERE data_cancelamento IS NOT NULL
)
SELECT
    CAST(STRFTIME('%Y', referencia) AS INTEGER) AS ano,
    CAST(STRFTIME('%m', referencia) AS INTEGER) AS mes,
    SUM(abertos) AS total_abertos,
    SUM(fechados) AS total_fechados,
    SUM(cancelados) AS total_cancelados
FROM eventos
GROUP BY referencia
ORDER BY referencia;

CREATE VIEW vw_chamados_abertos_dia AS
SELECT
    DATE(data_abertura) AS data,
    CAST(STRFTIME('%Y', data_abertura) AS INTEGER) AS ano,
    CAST(STRFTIME('%m', data_abertura) AS INTEGER) AS mes,
    CAST(STRFTIME('%W', data_abertura) AS INTEGER) + 1 AS semana,
    CASE STRFTIME('%w', data_abertura)
        WHEN '0' THEN 7 ELSE CAST(STRFTIME('%w', data_abertura) AS INTEGER)
    END AS dia_semana,
    COUNT(*) AS total_abertos
FROM vw_relatorio_chamados_geral
GROUP BY DATE(data_abertura)
ORDER BY data;

CREATE VIEW vw_chamados_abertos_semana AS
SELECT
    CAST(STRFTIME('%Y', data_abertura, '-3 days', 'weekday 4') AS INTEGER) AS ano,
    CAST(STRFTIME('%W', data_abertura) AS INTEGER) + 1 AS semana,
    DATE(data_abertura, '-' || ((CAST(STRFTIME('%w', data_abertura) AS INTEGER) + 6) % 7) || ' days') AS inicio_semana,
    DATE(data_abertura, '-' || ((CAST(STRFTIME('%w', data_abertura) AS INTEGER) + 6) % 7) || ' days', '+6 days') AS fim_semana,
    COUNT(*) AS total_abertos
FROM vw_relatorio_chamados_geral
GROUP BY inicio_semana
ORDER BY inicio_semana;

CREATE VIEW vw_produtividade_tecnicos AS
SELECT
    tecnico_id,
    tecnico_nome,
    COUNT(*) AS total_atribuidos,
    SUM(chamado_concluido) AS total_concluidos,
    SUM(chamado_em_aberto) AS total_em_andamento,
    ROUND(AVG(CASE WHEN chamado_concluido = 1 THEN tempo_resolucao_horas END), 2) AS tempo_medio_resolucao_horas,
    ROUND(AVG(tempo_primeira_resposta_horas), 2) AS tempo_medio_primeira_resposta_horas,
    SUM(CASE WHEN nota_atendimento IS NOT NULL THEN 1 ELSE 0 END) AS total_avaliacoes,
    ROUND(AVG(nota_atendimento), 2) AS nota_media
FROM vw_relatorio_chamados_geral
WHERE tecnico_id IS NOT NULL
GROUP BY tecnico_id, tecnico_nome;

CREATE VIEW vw_avaliacoes_tecnicos AS
SELECT
    t.id AS chamado_id,
    t.hash AS numero_chamado,
    t.evaluated_at AS data_avaliacao,
    t.closed_at AS data_fechamento,
    t.satisfaction_rating AS nota,
    CASE WHEN t.satisfaction_comment LIKE 'Avaliacao automatica:%' THEN 1 ELSE 0 END AS avaliacao_automatica,
    t.assigned_to_id AS tecnico_id,
    CASE
        WHEN technician.id IS NULL THEN NULL
        ELSE COALESCE(NULLIF(TRIM(COALESCE(technician.first_name, '') || ' ' || COALESCE(technician.last_name, '')), ''), technician.username)
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

CREATE VIEW vw_notas_tecnicos AS
SELECT
    tecnico_id,
    tecnico_nome,
    COUNT(*) AS total_avaliacoes,
    ROUND(AVG(nota), 2) AS nota_media,
    MIN(nota) AS menor_nota,
    MAX(nota) AS maior_nota,
    SUM(CASE WHEN nota = 1 THEN 1 ELSE 0 END) AS notas_1,
    SUM(CASE WHEN nota = 2 THEN 1 ELSE 0 END) AS notas_2,
    SUM(CASE WHEN nota = 3 THEN 1 ELSE 0 END) AS notas_3,
    SUM(CASE WHEN nota = 4 THEN 1 ELSE 0 END) AS notas_4,
    SUM(CASE WHEN nota = 5 THEN 1 ELSE 0 END) AS notas_5,
    SUM(CASE WHEN nota >= 4 THEN 1 ELSE 0 END) AS notas_4_5,
    ROUND((SUM(CASE WHEN nota >= 4 THEN 1 ELSE 0 END) * 100.0) / NULLIF(COUNT(*), 0), 2) AS percentual_notas_4_5,
    SUM(avaliacao_automatica) AS avaliacoes_automaticas,
    MAX(data_avaliacao) AS ultima_avaliacao
FROM vw_avaliacoes_tecnicos
GROUP BY tecnico_id, tecnico_nome;

CREATE VIEW vw_chamados_em_atraso AS
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
            ELSE COALESCE(NULLIF(TRIM(COALESCE(technician.first_name, '') || ' ' || COALESCE(technician.last_name, '')), ''), technician.username)
        END AS tecnico_nome,
        t.created_at AS data_abertura,
        (
            t.resolution_paused_seconds
            + CASE
                WHEN t.resolution_paused_at IS NULL THEN 0
                ELSE MAX((JULIANDAY(CURRENT_TIMESTAMP) - JULIANDAY(t.resolution_paused_at)) * 86400.0, 0)
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
    DATETIME(
        data_abertura,
        PRINTF('+%d minutes', prazo_sla_minutos),
        PRINTF('+%d seconds', CAST(pausa_resolucao_segundos AS INTEGER))
    ) AS prazo_sla,
    ROUND(
        MAX(
            ((JULIANDAY(CURRENT_TIMESTAMP) - JULIANDAY(data_abertura)) * 86400.0) - pausa_resolucao_segundos,
            0
        ) / 3600.0,
        2
    ) AS horas_em_aberto,
    CASE
        WHEN MAX(
            ((JULIANDAY(CURRENT_TIMESTAMP) - JULIANDAY(data_abertura)) * 86400.0) - pausa_resolucao_segundos,
            0
        ) > (prazo_sla_minutos * 60)
        THEN 1 ELSE 0
    END AS atrasado
FROM chamados;

CREATE VIEW dim_calendario AS
WITH RECURSIVE datas(data) AS (
    SELECT DATE('2024-01-01')
    UNION ALL
    SELECT DATE(data, '+1 day') FROM datas WHERE data < DATE('2035-12-31')
)
SELECT
    data,
    CAST(STRFTIME('%Y', data) AS INTEGER) AS ano,
    CAST(STRFTIME('%m', data) AS INTEGER) AS mes,
    CASE CAST(STRFTIME('%m', data) AS INTEGER)
        WHEN 1 THEN 'Janeiro' WHEN 2 THEN 'Fevereiro' WHEN 3 THEN 'Março'
        WHEN 4 THEN 'Abril' WHEN 5 THEN 'Maio' WHEN 6 THEN 'Junho'
        WHEN 7 THEN 'Julho' WHEN 8 THEN 'Agosto' WHEN 9 THEN 'Setembro'
        WHEN 10 THEN 'Outubro' WHEN 11 THEN 'Novembro' ELSE 'Dezembro'
    END AS nome_mes,
    ((CAST(STRFTIME('%m', data) AS INTEGER) - 1) / 3) + 1 AS trimestre,
    CAST(STRFTIME('%W', data) AS INTEGER) + 1 AS semana,
    CAST(STRFTIME('%d', data) AS INTEGER) AS dia,
    CASE STRFTIME('%w', data) WHEN '0' THEN 7 ELSE CAST(STRFTIME('%w', data) AS INTEGER) END AS dia_semana,
    CASE STRFTIME('%w', data)
        WHEN '0' THEN 'Domingo' WHEN '1' THEN 'Segunda-feira' WHEN '2' THEN 'Terça-feira'
        WHEN '3' THEN 'Quarta-feira' WHEN '4' THEN 'Quinta-feira' WHEN '5' THEN 'Sexta-feira'
        ELSE 'Sábado'
    END AS nome_dia_semana,
    CASE WHEN STRFTIME('%w', data) IN ('0', '6') THEN 1 ELSE 0 END AS eh_final_de_semana
FROM datas;
