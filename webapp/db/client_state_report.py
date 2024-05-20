from sqlalchemy import select, text
from db.db_schema import DbClient, DbGitCommit, DbClientCommitAccess, DbClientAuthEvent, DbAuthState, DbClientStateView
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from functools import wraps

# SQL literal for generating a report on 
REPORT_SQL = """
WITH latest_auth AS (
    SELECT client_auth_sessions.* FROM client
    LEFT JOIN client_auth_sessions ON client.id = client_auth_sessions.client_id
    WHERE client_auth_sessions.id = (
        SELECT id FROM client_auth_sessions
        WHERE client_auth_sessions.client_id = client.id
        AND initiated <= :report_time
        ORDER BY initiated DESC
        LIMIT 1
    )
), latest_commit AS (
    SELECT client_commit_access.* FROM client
    LEFT JOIN client_commit_access ON client.id = client_commit_access.client_id
    WHERE client_commit_access.id = (
        SELECT id FROM client_commit_access
        WHERE client_commit_access.client_id = client.id
        AND access_time <= :report_time
        ORDER BY access_time DESC
        LIMIT 1
    )
)
SELECT 
    client.id, client.name,
    latest_auth.auth_state, latest_auth.initiated, latest_auth.expires,
    latest_commit.commit_hash, latest_commit.access_time
FROM client
LEFT JOIN latest_auth ON latest_auth.client_id = client.id
LEFT JOIN latest_commit ON latest_commit.client_id = client.id
WHERE (:auth_state IS NULL OR latest_auth.auth_state = :auth_state)
AND   (:commit_hash IS NULL OR latest_commit.commit_hash = :commit_hash)
"""

def query_client_states(session: Session, report_time: datetime = None, auth_state: DbAuthState = None, latest_commit: bool = None) -> list[DbClientStateView]:
    """ Query the database for the last-reported state of every client at the given timestamp,
    optionally filtering on a given state """
    report_timestamp = report_time or datetime.now()

    commit_hash = session.scalars(select(DbGitCommit)
        .where(DbGitCommit.commit_time <= report_timestamp)
        .order_by(DbGitCommit.commit_time.desc())
        .limit(1)).first().commit_hash if latest_commit else None

    return session.query(DbClientStateView).from_statement(text(REPORT_SQL)).params({
        'report_time': report_timestamp,
        'auth_state': auth_state,
        'commit_hash': commit_hash
    }).all()
 

