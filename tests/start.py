import logging
from survtur_glacier import start

logging.getLogger('botocore').level = logging.INFO
logging.getLogger('urllib3').level = logging.INFO
logging.basicConfig(level=logging.DEBUG)

start()
