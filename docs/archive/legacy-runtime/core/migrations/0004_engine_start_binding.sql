ALTER TABLE runs ADD COLUMN engine_namespace text;
ALTER TABLE runs ADD COLUMN first_start_at timestamptz;

UPDATE runs r SET first_start_at=t.created_at
FROM tasks t WHERE r.task_id=t.id AND r.workflow_id IS NOT NULL;
