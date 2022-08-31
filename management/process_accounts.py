#!/usr/bin/env python

import sys
import os
from shutil import rmtree, copy
from time import localtime
from inspect import getsource
from subprocess import run, check_output
import shlex

user_dirs = ['/home','/user/eleves']
base_dir = os.path.dirname(__file__)

def msg_exit(msg):
    print(msg)
    sys.exit(0)
    
def get_output(cmd):
    return check_output(shlex.split(cmd)).decode('utf-8').splitlines()
    
def remove_with_info(folder):
    if '-r' in sys.argv:
        print('Removing ' + folder)
        rmtree(folder)
    else:
        print('Would remove ' + folder + ' (use with -r to remove)')
        

if os.environ['USER'] != 'root':
    msg_exit('Execute this program as root to process user accounts')

year = localtime().tm_year


def align_ownership(home):
    user = os.path.basename(abs_home)
    try:
        get_output(f'id -u {user}')
        
        # remove students if very old profile
        if user[-4:].isdigit() and int(user[-4:]) < year-2:
            raise Exception('I want to go to except: block')
        
        run(['chown',user,f'{home}', '-R'])
        return False
    except:
        # user does not exist
        remove_with_info(home)
    return False

def clean_ros_logs(home):
    '''
    Remove ROS logs
    '''        
    ros_cache = f'{home}/.ros/log'
    if os.path.exists(ros_cache):
        remove_with_info(ros_cache)
    return True
        
def update_bashrc_geany(home):
    '''
    Update .bashrc file for ros_management_tools
    '''
    bashrc = f'{home}/.bashrc'
    if not os.path.exists(bashrc): return False
    
    with open(bashrc) as f:
        content = f.read().splitlines()
        
    ros_default = '-ros1'
    if any([line.startswith('ros1ws') for line in content]):
        ros_default = '-ros1'
    elif any([line.startswith('ros2ws') for line in content]):
        ros_default = '-ros2'    
        
    updated = False
    for i,line in enumerate(content):
        line = line.split('#')[0].strip()
        if line.startswith('source') and line.endswith('ros_management.bash'):
            line = f'{line} -k -p {ros_default} -lo' 
            updated = True
        elif line.startswith('source') and 'ros_management.bash' in line and '-lo' not in line:
            line += ' -lo'
            updated = True            
        else:
            for ros in ('1','2'):
                if line == f'ros{ros}ws':
                    line = ''
                    updated = True
        if '/opt/local_ws' in line:
            line = line.replace('/opt/local_ws', '/opt/ecn')
            updated = True
            
        if updated:
            content[i] = line       
            
    if updated:
        print(f'Updating {bashrc}')
        with open(bashrc, 'w') as f:
            f.write('\n'.join(content))
        
    # also updates geany configuration    
    geany_conf = ['.config/geany/geany.conf', '.config/geany/filedefs/filetypes.common']
    updated = False
    distro = get_output('lsb_release -cs')[0]
    for conf in geany_conf:
        dst = f'{home}/{conf}'
        src = f'{base_dir}/../skel/{distro}/{conf}'
        if not os.path.exists(dst):
            print(f'   Creating {dst}')
            updated = True
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            copy(src, dst)
            
    return updated or '-f' in sys.argv
        
def sync_desktop(home):
    src = '.config/xfce4/xfconf/xfce-perchannel-xml'
    dst = f'{home}/{src}'
    if not os.path.exists(dst): 
        return False
    
    copy(f'/etc/skel/{src}/xfce4-desktop.xml', dst)
    return True

fct_called = update_bashrc_geany
#fct_called = sync_sdesktop

if '--ownership' in sys.argv:
    fct_called = align_ownership
    
if '--roslog' in sys.argv:
    fct_called = clean_ros_logs
    
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
                if fct_called(abs_home):
                    align_ownership(abs_home)
                    

    


