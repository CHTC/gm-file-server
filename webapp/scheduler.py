from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler

from util.git_utils import sync_repo
from util.httpd_utils import prune_auth_file




def init_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_repo, CronTrigger(minute="*", hour="*"))
    scheduler.add_job(prune_auth_file, CronTrigger(minute="*", hour="*"))
    scheduler.start()
