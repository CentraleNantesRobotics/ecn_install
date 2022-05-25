#!/usr/bin/env python

import sys
import os
from shutil import rmtree, copy
from time import localtime
from inspect import getsource
from subprocess import run

user_dirs = ['/home','/user/eleves']
base_dir = os.path.dirname(__file__)

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
    msg_exit('Execute this program as root to process user accounts')

year = localtime().tm_year


def clean_accounts(home):
    '''
    Remove ROS logs and old student accounts (< year-2)
    '''    
    # try to get student year, if any
    if '-s' in sys.argv:
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
        
def update_bashrc_geany(home):
    '''
    Update .bashrc file for ros_management_tools
    '''
    bashrc = f'{home}/.bashrc'
    if not os.path.exists(bashrc): return
    
    with open(bashrc) as f:
        content = f.read().splitlines()
    
    ros_default = ''
    if any([line.startswith('ros1ws') for line in content]):
        ros_default = ' -ros1'
    elif any([line.startswith('ros2ws') for line in content]):
        ros_default = ' -ros2'    
        
    updated = False
    for i,line in enumerate(content):
        line = line.split('#')[0].strip()
        if line.startswith('source') and line.endswith('ros_management.bash'):
            content[i] = line + ' -k -p' + ros_default
            updated = True
        else:
            for ros in ('1','2'):
                if line == f'ros{ros}ws':
                    content[i] = ''
                    updated = True
    
    if updated:
        print(f'Updating {bashrc}')
        with open(bashrc, 'w') as f:
            f.write('\n'.join(content))
        
    # also updates geany configuration    
    geany_conf = ['.config/geany/geany.conf', '.config/geany/filedefs/filetypes.common']
    updated = False
    for conf in geany_conf:
        dst = f'{home}/{conf}'
        src = f'{base_dir}/../skel/{conf}'
        if not os.path.exists(dst):
            print(f'Creating {dst}')
            updated = True
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            copy(src, dst)    
    
    if updated or '-f' in sys.argv:
        user = os.path.basename(home)
        run(['chown',user,f'{home}/.config/geany', '-R'])
    

#fct_called = clean_accounts
fct_called = update_bashrc_geany
    
print('Will execute following function on user accounts:\n')

print(getsource(fct_called))

r = input('\nConfirm [Y/n] ')
if r in ('n','N'):
    sys.exit(0)

for home in user_dirs:
    if os.path.exists(home):
        for sub in os.listdir(home):
            abs_home = f'{home}/{sub}'
            if os.path.isdir(abs_home):
                fct_called(abs_home)