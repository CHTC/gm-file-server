from db.db import DbSession
from sqlalchemy import select, text
from db.db_schema import DbClient, DbGitCommit, DbClientCommitAccess, DbClientAuthEvent, DbAuthState, DbClientStateView
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from functools import wraps

CLIENT_COUNT = 100
COMMIT_COUNT = 75
AUTH_COUNT = 500

START_TIME = datetime.now()

def with_time_logging(func):
    @wraps(func)
    def _log_time(*args,**kwargs):
        start_time = datetime.now()
        print(f"Starting {func} at {start_time}")
        try:
            func(*args, **kwargs)
        finally:
            print(f"Elapsed: {datetime.now() - start_time }")
    return _log_time


def _add_git_commits(session: Session, client: DbClient):
    for i in range(COMMIT_COUNT):
        session.add(DbClientCommitAccess(client.id, f"{i}", START_TIME - timedelta(days = i)))


def _add_access_logs(session: Session, client: DbClient):
    for i in range(AUTH_COUNT):
        auth_event = DbClientAuthEvent(client.id)
        auth_event.auth_state = DbAuthState.ACTIVE
        auth_event.initiated = START_TIME - timedelta(hours=2*i)
        auth_event.expires = auth_event.initiated + timedelta(hours=2)
        session.add(auth_event)

@with_time_logging
def populate_db():
    with DbSession() as session:
        # Add Git Commits
        for i in range(COMMIT_COUNT):
            session.add(DbGitCommit(f"{i}", START_TIME - timedelta(days = i)))

        for i in range(CLIENT_COUNT):
            client = DbClient(f"{i}")
            session.add(client)
            _add_git_commits(session, client)
            _add_access_logs(session, client)
        session.commit()

def print_db_stats():
    with DbSession() as session:
        print(f"Client Count: {session.query(DbClient.id).count()}")
        print(f"Commit Access Count: {session.query(DbClientCommitAccess.id).count()}")
        print(f"Auth Event Count: {session.query(DbClientAuthEvent.id).count()}")

@with_time_logging
def find_latest_auth_iter():
    with DbSession() as session:
        auth_sessions = []
        client_ids = session.scalars(select(DbClient.id))
        for id in client_ids:
            auth_sessions.append(session.scalar(select(DbClientAuthEvent)
                .where(DbClientAuthEvent.client_id == id)
                .order_by(DbClientAuthEvent.initiated.desc())
                .limit(1)))
        print(len(auth_sessions))

@with_time_logging
def find_latest_auth_window():
    with DbSession() as session:
        auth_sessions = session.query(DbClientAuthEvent).from_statement(text("""
            WITH ordered_auth AS (
                SELECT *, row_number() over (partition by client_id order by initiated desc) as row_num
                FROM client_auth_sessions
            )
            SELECT * FROM ordered_auth where row_num = 1"""
        )).all()
        print(len(auth_sessions))

@with_time_logging
def find_latest_auth_inner_query():
    with DbSession() as session:
        auth_sessions = session.query(DbClientStateView).from_statement(text("""
        WITH latest_auth AS (
            SELECT client_auth_sessions.* FROM client
            LEFT JOIN client_auth_sessions ON client.id = client_auth_sessions.client_id
            WHERE client_auth_sessions.id = (
                SELECT id FROM client_auth_sessions
                WHERE client_auth_sessions.client_id = client.id
                ORDER BY initiated DESC
                LIMIT 1
            )
        ), latest_commit AS (
            SELECT client_commit_access.* FROM client
            LEFT JOIN client_commit_access ON client.id = client_commit_access.client_id
            WHERE client_commit_access.id = (
                SELECT id FROM client_commit_access
                WHERE client_commit_access.client_id = client.id
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
        """)).all()
        print(len(auth_sessions))
if __name__ == '__main__':
    populate_db()
    print_db_stats()
    find_latest_auth_iter()
    find_latest_auth_window()
    find_latest_auth_inner_query()
