from pprint import pprint
from threading import *
import base64
import datetime
import dill
import logging
import swagbot.database.scheduler as db
import swagbot.globals as globals
import swagbot.utils.scheduler as utils
import time

class Scheduler(object):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', 'scheduler')
        self.scheduler_thread = Thread(
            name=self.name,
            target=self.scheduler,
            daemon=True
        )
        self.thread_started = False
        globals.schedulers[self.name] = self

    def add_job(self, module=None, name=None, interval=None, function=None, channels=[], enabled=None):
        logging.info(f'Adding the scheduled job {module}.{name}.')
        db.add_job(module=module, name=name, interval=interval, function=function, enabled=enabled)
        if not utils.job_exists(module=module, name=name):
            logging.info(f'Failed to add the scheduled job {module}.{name}.')
    
    def delete_job(self, module=None, name=None):
        if utils.job_exists(module=module, name=name):
            db.delete_job(module=module, name=name)
            if utils.job_exists(module=module, name=name):
                logging.info(f'Failed to delete the scheduled job {module}.{name}.')
        else:
            logging.error(f'The scheduled job {module}.{name} doesn\'t exist.')

    def scheduler(self):
        while self.thread_started:
            if self.scheduler_thread.is_alive():
                now = datetime.datetime.now()
                jobs = db.get_jobs_by_module(module=self.name)
                for job in jobs:
                    if (now.minute % job['interval']) == 0 and now.second == 0:
                        if job['enabled']:
                            logging.info(f'Executing the job {job["module"]}.{job["name"]}.')
                            try:
                                decoded = dill.loads(base64.b64decode(job['function']))
                                fn, args = decoded
                                fn(*args)
                            except Exception as e:
                                logging.error(f'Failed to execute the job {job["module"]}.{job["name"]}: {e}')
                        else:
                            logging.info(f'The job {job["module"]}.{job["name"]} is disabled. Skipping.')
            time.sleep(1)
    
    def job_count(self):
        jobs = self.get_jobs(module=self.name)
        return len(jobs)

    def start(self):
        plural = 'job' if self.job_count() == 1 else 'jobs'
        # logging.info(f'Starting the scheduler {self.name} with {self.job_count()} {plural}.')
        self.thread_started = True
        self.scheduler_thread.start()
        if not self.scheduler_thread.is_alive():
            self.thread_id = self.scheduler_thread.native_id
            logging.error(f'Failed to start the scheduler {self.name}.')
        else:
            logging.info(f'Started the scheduler {self.name} with {self.job_count()} {plural}.')
    
    def stop(self):
        logging.info(f'Stopping the scheduler {self.name}.')
        self.thread_started = False
        self.scheduler_thread.join(timeout=0)
    
    def pause(self):
        logging.info(f'Pausing the scheduler {self.name}.')
        self.thread_started = False
    
    def resume(self):
        logging.info(f'Resuming the scheduler {self.name}.')
        self.thread_started = True

    # Common functions need to be in a module accessible by all
    def job_exists(self, module=None, name=None):
        return utils.job_exists(module=module, name=name)
    
    def job_exists_by_id(self, id=None):
        return utils.job_exists_by_id(id=id)
    
    def job_enabled(self, module=None, name=None):
        return utils.job_enabled_by_id(module=module, name=name)

    def job_enabled_by_id(self, id=None):
        return utils.job_enabled_by_id(id=id)
    
    def get_jobs(self, module=None, name=None):
        return utils.get_jobs(module=module, name=name)
    
    def get_job_by_id(self, id=None):
        return utils.get_job_by_id(id=id)
    
    def get_job_channels(self, module=None, name=None):
        return utils.get_job_channels(module=module, name=name)

    def delete_jobs_for_module(self, module=None):
        return utils.delete_jobs_for_module(module=module)
