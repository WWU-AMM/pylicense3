#!/usr/bin/env python

# pylicense (https://github.com/ftalbrecht/pylicense): addheader.py
# Copyright Holders: Felix Albrecht
# License: BSD 2-Clause License (http://opensource.org/licenses/BSD-2-Clause)

'''
Add header to a given file.

Usage:
    addheader.py [-hv] [--help] [--verbose] --cfg=CONFIG_FILE DIR


Arguments:
    DIR             Directory to process.

Options:
    -h, --help      Show this message.

    -v, --verbose   Be verbose.
'''


from __future__ import print_function
import ConfigParser
from docopt import docopt
from shutil import copyfile
import subprocess
import os
import sys
import re
import fnmatch

def process_dir(dirname, config):
    os.chdir(dirname)
    include = re.compile('|'.join(fnmatch.translate(p) for p in config.get('files', 'include_patterns').split()))
    exclude = re.compile('|'.join(fnmatch.translate(p) for p in config.get('files', 'exclude_patterns').split()))
    for root, _, files in os.walk(dirname):
        for abspath in [os.path.join(root, f) for f in files]:
            if include.match(abspath) and not exclude.match(abspath):
                yield abspath, process_file(abspath, config, dirname)


def add_multiple_authors(author_list, prefix, first_line_label, target, max_width):
    num_authors = len(author_list)
    assert num_authors > 0
    line = '{p} {label}: {first_author}'.format(p=prefix, label=first_line_label, first_author=author_list[0])
    if num_authors > 1:
        line = line + ','
    line_prefix = '{p}                   '.format(p=prefix)
    for ii in range(1, num_authors):
        author = author_list[ii]
        postfix = ''
        if ii < num_authors - 1:
            postfix = ','
        else:
            postfix = ''
        if len(line + ' ' + author + postfix) <= max_width:
            line = line + ' ' + author + postfix
        else:
            target.write(line + '\n')
            line = line_prefix + ' ' + author + postfix
    target.write(line + '\n')


def process_file(filename, config, root):
    assert(config.has_option('header', 'name'))
    project_name = config.get('header', 'name').strip()
    assert(config.has_option('header', 'license'))
    license = config.get('header', 'license').strip()
    url = config.get('header', 'url').strip() if config.has_option('header', 'license') else None
    max_width = int(config.get('header', 'max_width')) if config.has_option('header', 'max_width') else 78
    try:
        copyright_holders = [name.strip() for name in config.get('header', 'copyright_holders').strip().split(',')]
        if len(copyright_holders) == 0:
            raise Exception('ERROR: no copyright holders given!')
    except:
        raise Exception('ERROR: no copyright holders given!')
    list_contributors = False
    if config.has_option('header', 'list_contributers'):
        list_contributors = config.getboolean('header', 'list_contributers')
    contributors = []
    if list_contributors:
        try:
            ret = subprocess.Popen('git blame ' + filename + ' | perl -n -e \'/\\s\\((.*?)\\s[0-9]{4}/ && print \"$1\\n"\' | uniq',
                                    shell=True,
                                    cwd=root,
                                    stdout=subprocess.PIPE,
                                    stderr=sys.stderr)
            out, _ = ret.communicate()
            contributors = out.strip().split('\n')
            for ii in range(len(contributors)):
                contributors[ii] = contributors[ii].strip()
            contributors = list(set(contributors))
            contributors = [x for x in contributors if x not in copyright_holders]
            list_contributors = True if len(contributors) > 0 else False
        except:
            print('WARNING: there was a git related error, contributors will not be listed!')
            list_contributors = False
    prefix = '#'
    if config.has_option('header', 'prefix'):
        prefix = config.get('header', 'prefix')

    # create backup
    backup_filename = filename + '~'
    try:
        copyfile(filename, backup_filename)
    except:
        raise Exception('ERROR: could not create backup file \'{f}\'!'.format(backup_filename))
    # write header to original file
    with open(backup_filename, 'r') as source:
        with open(filename, 'w') as target:
            # project name and url
            line = '{p} {n}'.format(p=prefix, n=project_name)
            if url is not None:
                if len(line) + len(url) + len('().') <= max_width:
                    target.write('{line} ({url}).\n'.format(line=line, url=url))
                else:
                    target.write('{line}:\n'.format(line=line))
                    target.write('{prefix}   {url}\n'.format(prefix=prefix, url=url))
            # copyright holders
            add_multiple_authors(copyright_holders, prefix, 'Copyright holders', target, max_width)
            target.write('{p} License: {l}\n'.format(p=prefix, l=license))
            # contributors
            if list_contributors:
                target.write(prefix + '\n')
                add_multiple_authors(contributors, prefix, 'Contributors', target, max_width)
            target.write('\n')
            target.writelines(source.readlines())
    # remove backup
    try:
        os.remove(backup_filename)
    except:
        return 1
    return 0

if __name__ == '__main__':
    # parse arguments
    args = docopt(__doc__)
    verbose = False
    if args['--verbose']:
        verbose = True
    config = ConfigParser.SafeConfigParser()
    if args['--cfg'] is not None:
        config.readfp(open(args['--cfg']))
    else:
        raise Exception('ERROR: no suitable config file given (try \'--cfg CONFIG_FILE\')!')
    dirname = args['DIR']
    for fn, res in process_dir(dirname, config):
        print('{}: {}'.format(fn, 'failed' if res else 'success'))
