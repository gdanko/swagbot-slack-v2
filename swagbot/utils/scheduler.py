import swagbot.database.scheduler as db
import swagbot.utils.core as utils

def list(module=None, name=None):
    list_output = []
    results = db.get_jobs(module=module, name=name)
    if results:
        if len(results) > 0:
            for result in results:
                result['enabled'] = 'Enabled' if result['enabled'] == 1 else 'Disabled'
            for chunk in utils.chunker(results, 25):
                output = []
                for job in chunk:
                    output.append([
                        job['id'],
                        job['module'],
                        job['name'],
                        job['interval'],
                        job['enabled'],
                    ])
                list_output.append(utils.generate_table(headers=['Job ID', 'Module', 'Name', 'Interval', 'Status'], data=output))
        return list_output
    else:
        return False

def enable(id=None):
    if job_exists_by_id(id=id):
        if not job_enabled_by_id(id=id):
            job = get_job_by_id(id=id)
            if job:
                db.enable_job(module=job['module'], name=job['name'])
                if job_enabled_by_id(id=id):
                    return True, f'The scheduled job {job["module"]}.{job["name"]} was successfully enabled.'
                else:
                    return False, f'Failed to enable the scheduled job {job["module"]}.{job["name"]}.'
            else:
                return False, (f'The scheduled job with the ID {id} could not be found.')
        else:
            return False, (f'The scheduled job {job["module"]}.{job["name"]} isn\'t currently enabled.')
    else:
        return False, (f'The scheduled job The scheduled job with the ID {id} could not be found.')

def disable(id=None):
    if job_exists_by_id(id=id):
        if job_enabled_by_id(id=id):
            job = get_job_by_id(id=id)
            if job:
                db.disable_job(module=job['module'], name=job['name'])
                if not job_enabled_by_id(id=id):
                    return True, (f'The scheduled job {job["module"]}.{job["name"]} was successfully disabled.')
                else:
                    return False, (f'Failed to disable the scheduled job {job["module"]}.{job["name"]}.')
            else:
                return False, (f'The scheduled job with the ID {id} could not be found.')
        else:
            return False, (f'The scheduled job {job["module"]}.{job["name"]} isn\'t currently disabled.')
    else:
        return False, (f'The scheduled job with the ID {id} could not be found.')

def job_exists(module=None, name=None):
    job = db.get_jobs(module=module, name=name)
    return True if job else False

def job_exists_by_id(id=None):
    job = get_job_by_id(id=id)
    return True if job else False

def job_enabled(module=None, name=None):
    job = db.get_jobs(module=module, name=name)
    if job:
        return True if job[0]['enabled'] == 1 else False
    else:
        return False

def job_enabled_by_id(id=None):
    job = db.get_job_by_id(id=id)
    if job:
        return True if job['enabled'] == 1 else False
    else:
        return False

def get_jobs(module=None, name=None):
    jobs = db.get_jobs(module=module, name=name)
    if jobs and len(jobs) > 0:
        return jobs
    else:
        return False

def get_job_by_id(id=None):
    jobs = db.get_job_by_id(id=id)
    if jobs and len(jobs) > 0:
        return jobs
    else:
        return False

def get_job_channels(module=None, name=None):
    job_channels = db.get_job_channels(module=module, name=name)
    return job_channels

def delete_jobs_for_module(module=None):
    jobs = db.get_jobs(module=module)
    if jobs and len(jobs) > 0:
        db.delete_jobs_for_module(module=module)
        jobs = db.get_jobs(module=module)
        if jobs and len(jobs) > 0:
            return False, f'Failed to delete all scheduled jobs for {module}.'
        else:
            return True, ''
    else:
        return True, f'No scheduled jobs found for {module}.'
