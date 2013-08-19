#!/usr/bin/env python
#
# Run fedora-review using -rpn flags on package directories
# generated by dist-check-setup. Typical usage:
#
#    $ mkdir work; cd work
#    $ dist-check-setup
#    # --  wait for hours
#    $ export REVIEW_LOGLEVEL=warning
#    $ ls -d * | dist-check-run
#    # -- wait for at least 24 hours...
#
# Script silently drops directories not deemed as usable.
#
# Script uses --prebuilt, mock calls can be avoided by installing a
# dummy mock script; see README.
#
# pylint: disable=C0103,C0111,W1201,W0702,W0621

import logging
import multiprocessing
import os
import os.path
import re
import shutil
import subprocess
import sys

from glob import glob

ARCH = subprocess.check_output(['uname', '-i']).strip()
YUM_DL_CMD = 'yumdownloader --disablerepo=* --enablerepo=fedora*' \
             ' --quiet --releasever=rawhide --archlist=%s' % ARCH
LOGLEVEL = logging.INFO
LOGFORMAT = "%(levelname)s:dist-check-run: %(message)s"


def fetch(url):
    subprocess.check_call(['wget', '-q', '-N', url])


def fetch_packages(packages, source=False):
    cmd = YUM_DL_CMD
    if source:
        cmd += ' --source '
        cmd += packages[0]
    else:
        for p in packages:
            cmd += ' ' + p + '.noarch'
            cmd += ' ' + p + '.' + ARCH
    subprocess.check_output(cmd.split())


def download_urls(pkg):
    ''' Download all urls listed in pkg/urls. '''
    pkg = pkg.strip()
    logging.info("Downloading URL:s for " + pkg)
    startdir = os.getcwd()
    os.chdir(pkg)
    packages = []
    error = None
    for path in glob('*.url'):
        path = path.strip()
        if path == 'srpm.url':
            try:
                fetch_packages([pkg], source=True)
            except subprocess.CalledProcessError as cpe:
                error = cpe
        else:
            packages.append(re.sub(r'\.url$', '', path))
    try:
        fetch_packages(packages)
    except subprocess.CalledProcessError as cpe:
        error = cpe

    os.chdir(startdir)
    if error:
        logging.warning("Download error on %s: %s" % (pkg, error.__str__()))
        with open(pkg + '/urlerror', 'w') as f:
            f.write(error.__str__())
        for rpm in glob(pkg + '/*.rpm'):
            os.unlink(rpm)
    logging.info("Done: downloading URL:s for " + pkg)


def run_review(pkg):
    pkg = pkg.strip()
    logging.info("Starting review: " + pkg)
    if os.path.exists(pkg + '/urlerror'):
        logging.warning("Skipping %s (download errors)" % pkg)
        os.unlink(pkg + '/urlerror')
        return
    startdir = os.getcwd()
    os.chdir(pkg)
    if os.path.exists(pkg):
        shutil.rmtree(pkg)
    srpm = glob("*.src.rpm")[0]
    os.environ['XDG_CACHE_HOME'] = os.getcwd()
    cmd = "try-fedora-review -B -rpn  %s " % srpm
    cmd += "-m fedora-rawhide-%s " % ARCH
    cmd += "-D DISTTAG=fc20 "
    cmd += '-x '
    cmd += "CheckBuild,"
    cmd += "CheckPackageInstalls,"
    cmd += "CheckRpmlintInstalled,"
    cmd += "CheckNoNameConflict,"
    cmd += "CheckOwnDirs,"
    cmd += "CheckInitDeps,"
    cmd += "CheckRpmlint"
    try:
        subprocess.check_call(cmd.split())
    except:
        logging.error("Can't run review cmd: " + cmd)
    else:
        resultdir = "../" + pkg + ".results"
        if os.path.exists(resultdir):
            shutil.rmtree(resultdir)
        os.mkdir(resultdir)
        for f in [pkg + '/review.txt', 'fedora-review.log']:
            if os.path.exists(f):
                shutil.move(f, resultdir)
        shutil.rmtree(pkg)
        for rpm in glob('*.rpm'):
            os.unlink(rpm)
    finally:
        os.chdir(startdir)

logging.basicConfig(level=LOGLEVEL, format=LOGFORMAT)
prev = None
for d in sys.stdin:
    d = d.strip()
    if not glob(d + '/*.url')  or '.tmp.' in d:
        logging.info("Skipping unusable path: " + d)
        continue
    if '/' in d:
        d = d.rsplit('/', 1)[1]
    if os.path.exists(d + '.results'):
        logging.info("Skipping already run " + d)
        continue
    pkg = d
    pool = multiprocessing.Pool(4)
    if prev:
        pool.apply_async(run_review, (prev,))
    pool.apply_async(download_urls, (pkg,))
    pool.close()
    pool.join()
    prev = pkg
if prev:
    run_review(prev)
