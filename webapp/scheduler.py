from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler

from util.git_utils import REPO_URL, SSH_KEY, sync_repo




def init_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_repo, CronTrigger(minute="*", hour="*"))
    scheduler.start()
