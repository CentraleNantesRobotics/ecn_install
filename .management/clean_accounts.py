#!/usr/bin/env python

import sys
import os
from shutil import rmtree
from time import localtime
from inspect import getsource

user_dirs = ['/home','/user/eleves']

def msg_exit(msg):
    print(msg)
    sys.exit(0)
    

def remove_with_info(folder):
    if '-r' in sys.argv:
        print('Removing ' + folder)
        rmtree(folder)
    else:
        print('Would remove ' + folder)
        

if os.environ['USER'] != 'root':
    msg_exit('Execute this program as root to remove logs / old student accounts')

year = localtime().tm_year

def process(home):
    
    # try to get student year, if any
    name = os.path.basename(home)
    if name[-4:].isdigit():
        st_year = int(name[-4:])
        if st_year < year-2:
            # just remove this folder, user is from LDAP
            remove_with_info(home)
            return
    
    ros_cache = f'{home}/.ros/log'
    if os.path.exists(ros_cache):
        remove_with_info(ros_cache)
    
    
print('Will execute following function on user accounts:')
print(getsource(process))

r = input('\nConfirm [Y/n] ')
if r in ('n','N'):
    sys.exit(0)


for home in user_dirs:
    if os.path.exists(home):
        for sub in os.listdir(home):
            abs_home = f'{home}/{sub}'
            if os.path.isdir(abs_home):
                process(abs_home)
