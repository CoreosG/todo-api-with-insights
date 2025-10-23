-- Athena Queries for Todo API Analytics
-- These queries work against the Gold layer data lake
-- Database: todo_analytics
-- Workgroup: todo-analytics-workgroup

-- ===========================================
-- USER ANALYTICS QUERIES
-- ===========================================

-- Get all user analytics
SELECT * FROM user_analytics;

-- Get user count and summary
SELECT
    COUNT(*) as total_users,
    AVG(total_events) as avg_events_per_user,
    MAX(total_events) as max_events_per_user,
    MIN(total_events) as min_events_per_user
FROM user_analytics;

-- Get top active users
SELECT
    user_id,
    email,
    name,
    total_events,
    max_event_types
FROM user_analytics
ORDER BY total_events DESC
LIMIT 10;

-- ===========================================
-- TASK ANALYTICS QUERIES
-- ===========================================

-- Get all task metrics by user
SELECT * FROM task_analytics_user_metrics;

-- Get task completion summary
SELECT
    COUNT(*) as total_users_with_tasks,
    SUM(total_tasks) as total_tasks_across_all_users,
    SUM(completed_tasks) as total_completed_tasks,
    AVG(completed_tasks) as avg_completed_tasks_per_user,
    AVG(total_tasks) as avg_total_tasks_per_user
FROM task_analytics_user_metrics;

-- Get users with highest task completion rates
SELECT
    user_id,
    total_tasks,
    completed_tasks,
    ROUND(CAST(completed_tasks AS DOUBLE) / total_tasks * 100, 2) as completion_rate_percent
FROM task_analytics_user_metrics
WHERE total_tasks > 0
ORDER BY completion_rate_percent DESC
LIMIT 10;

-- Get task status distribution
SELECT
    'total_tasks' as metric,
    SUM(total_tasks) as value
FROM task_analytics_user_metrics
UNION ALL
SELECT
    'completed_tasks' as metric,
    SUM(completed_tasks) as value
FROM task_analytics_user_metrics
UNION ALL
SELECT
    'pending_tasks' as metric,
    SUM(pending_tasks) as value
FROM task_analytics_user_metrics
UNION ALL
SELECT
    'in_progress_tasks' as metric,
    SUM(in_progress_tasks) as value
FROM task_analytics_user_metrics;

-- ===========================================
-- CATEGORY ANALYTICS QUERIES
-- ===========================================

-- Get all category trends
SELECT * FROM task_analytics_category_trends;

-- Get most popular categories
SELECT
    category,
    total_tasks,
    completed_tasks,
    ROUND(CAST(completed_tasks AS DOUBLE) / total_tasks * 100, 2) as completion_rate_percent
FROM task_analytics_category_trends
ORDER BY total_tasks DESC;

-- ===========================================
-- BUSINESS METRICS QUERIES
-- ===========================================

-- Get all business KPIs
SELECT * FROM business_metrics_kpis;

-- Get business overview
SELECT
    metric,
    value
FROM business_metrics_kpis
ORDER BY metric;

-- ===========================================
-- COMBINED ANALYTICS QUERIES
-- ===========================================

-- Get user productivity (tasks completed per user)
SELECT
    ua.user_id,
    ua.email,
    ua.name,
    COALESCE(tam.total_tasks, 0) as total_tasks,
    COALESCE(tam.completed_tasks, 0) as completed_tasks,
    COALESCE(tam.pending_tasks, 0) as pending_tasks,
    COALESCE(tam.in_progress_tasks, 0) as in_progress_tasks
FROM user_analytics ua
LEFT JOIN task_analytics_user_metrics tam ON ua.user_id = tam.user_id
ORDER BY completed_tasks DESC;

-- Get users with no tasks
SELECT
    ua.user_id,
    ua.email,
    ua.name,
    ua.total_events
FROM user_analytics ua
LEFT JOIN task_analytics_user_metrics tam ON ua.user_id = tam.user_id
WHERE tam.user_id IS NULL
ORDER BY ua.total_events DESC;

-- ===========================================
-- SAMPLE QUERIES FOR DASHBOARD
-- ===========================================

-- Top 5 most productive users (by completed tasks)
SELECT
    ua.name,
    tam.completed_tasks,
    tam.total_tasks
FROM user_analytics ua
JOIN task_analytics_user_metrics tam ON ua.user_id = tam.user_id
ORDER BY tam.completed_tasks DESC
LIMIT 5;

-- Task completion rate by category
SELECT
    category,
    total_tasks,
    completed_tasks,
    ROUND(CAST(completed_tasks AS DOUBLE) / total_tasks * 100, 1) as completion_rate
FROM task_analytics_category_trends
WHERE total_tasks > 0
ORDER BY completion_rate DESC;

-- System health metrics
SELECT
    metric,
    CAST(value AS INTEGER) as value
FROM business_metrics_kpis
ORDER BY
    CASE metric
        WHEN 'total_users' THEN 1
        WHEN 'total_tasks' THEN 2
        WHEN 'completed_tasks' THEN 3
        ELSE 4
    END;
