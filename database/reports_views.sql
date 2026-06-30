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
    ROUND((EXTRACT(EPOCH FROM (t.closed_at - t.created_at)) / 3600.0)::numeric, 2) AS tempo_resolucao_horas,
    ROUND((EXTRACT(EPOCH FROM (t.first_response_at - t.created_at)) / 3600.0)::numeric, 2) AS tempo_primeira_resposta_horas,
    (LOWER(TRIM(st.name)) IN ('concluido', 'concluído', 'concluida', 'concluída', 'resolvido', 'resolvida', 'fechado', 'fechada', 'finalizado', 'finalizada')) AS chamado_concluido,
    (LOWER(TRIM(st.name)) IN ('cancelado', 'cancelada')) AS chamado_cancelado,
    (LOWER(TRIM(st.name)) NOT IN ('concluido', 'concluído', 'concluida', 'concluída', 'resolvido', 'resolvida', 'fechado', 'fechada', 'finalizado', 'finalizada', 'cancelado', 'cancelada')) AS chamado_em_aberto
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
    ROUND(AVG(tempo_primeira_resposta_horas), 2) AS tempo_medio_primeira_resposta_horas
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

CREATE OR REPLACE VIEW vw_produtividade_tecnicos AS
SELECT
    tecnico_id,
    tecnico_nome,
    COUNT(*) AS total_atribuidos,
    COUNT(*) FILTER (WHERE chamado_concluido) AS total_concluidos,
    COUNT(*) FILTER (WHERE chamado_em_aberto) AS total_em_andamento,
    ROUND(AVG(tempo_resolucao_horas) FILTER (WHERE chamado_concluido), 2) AS tempo_medio_resolucao_horas,
    ROUND(AVG(tempo_primeira_resposta_horas), 2) AS tempo_medio_primeira_resposta_horas
FROM vw_relatorio_chamados_geral
WHERE tecnico_id IS NOT NULL
GROUP BY tecnico_id, tecnico_nome;

CREATE OR REPLACE VIEW vw_chamados_em_atraso AS
SELECT
    t.id AS chamado_id,
    t.hash AS numero_chamado,
    sc.name AS titulo,
    st.name AS status,
    p.name AS prioridade,
    c.name AS categoria,
    CASE
        WHEN technician.id IS NULL THEN NULL
        ELSE COALESCE(NULLIF(TRIM(CONCAT_WS(' ', technician.first_name, technician.last_name)), ''), technician.username)
    END AS tecnico_nome,
    t.created_at AS data_abertura,
    t.created_at + MAKE_INTERVAL(mins => p.estimated_service_time) AS prazo_sla,
    ROUND((EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - t.created_at)) / 3600.0)::numeric, 2) AS horas_em_aberto,
    (CURRENT_TIMESTAMP > t.created_at + MAKE_INTERVAL(mins => p.estimated_service_time)) AS atrasado
FROM ticket_ticket t
JOIN ticket_ticket_status st ON st.id = t.status_id
JOIN registers_priority p ON p.id = t.priority_id
JOIN registers_subcategory sc ON sc.id = t.title_id
JOIN registers_category c ON c.id = sc.category_id
LEFT JOIN auth_user technician ON technician.id = t.assigned_to_id
WHERE LOWER(TRIM(st.name)) NOT IN ('concluido', 'concluído', 'concluida', 'concluída', 'resolvido', 'resolvida', 'fechado', 'fechada', 'finalizado', 'finalizada', 'cancelado', 'cancelada');

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
