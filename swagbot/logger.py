import logging

def dryrun(msg, *args, **kwargs):
    if logging.getLogger().isEnabledFor(logging.DRYRUN):
        logging.log(logging.DRYRUN, msg)

def configure(debug=False):
    log_level = logging.DEBUG if debug == True else logging.DRYRUN
    logging.basicConfig(
        level    = int(log_level),
        format   = '%(asctime)-15s [%(levelname)s] %(message)s',
        datefmt  = '%Y-%m-%d %H:%M:%S',
        handlers = [
            # logging.FileHandler('put your log path here'),
            logging.StreamHandler()
        ]
    )

logging.addLevelName(15, 'DRYRUN')
logging.dryrun = dryrun
logging.Logger.dryrun = dryrun
logging.DRYRUN = 15
