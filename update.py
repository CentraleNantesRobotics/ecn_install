#!/usr/bin/env python3
import yaml
import sys
import os
import shlex
import time
from shutil import rmtree
from threading import Thread
import re
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout,QHBoxLayout,QGridLayout, QLabel, QPushButton, QCheckBox, QComboBox, QSpacerItem, QSizePolicy, QInputDialog, QLineEdit
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtGui import QFont, QIcon
from subprocess import check_output, PIPE, Popen, DEVNULL

base_path = os.path.dirname(os.path.abspath(__file__))

ros1 = 'noetic'
ros2 = 'foxy'

class Display:
    
    user = os.environ['USER']
    show = False
    running = True
    cmd = ''
    delay = 0.2
    @staticmethod
    def init():        
        Display.user_offset = max(4, len(Display.user)) + 3 - len(Display.user)
        Display.sudo_offset = max(4, len(Display.user)) - 1
        # run blit thread
        Display.thread = Thread(target=Display.blit)
        Display.thread.start()
        
    @staticmethod
    def to_msg(cmd, sudo):
        if sudo:
            return f'\033[93m [sudo]{Display.sudo_offset*" "}\033[1;37;0m {cmd}'
        else:
            return f'\033[96m [{Display.user}]{Display.user_offset*" "}\033[1;37;0m {cmd}'
                
    @staticmethod
    def msg(cmd, sudo = False):
        if type(cmd) == list:
            Display.cmd = [Display.to_msg(cmd[0],sudo), Display.to_msg(' ↪ ' + cmd[1],sudo)]
        else:
            Display.cmd = Display.to_msg(cmd, sudo)        
        
    @staticmethod
    def blit():
        
        animations = ['◜◝◞◟','◣◤◥◢','▤▥▦▧▨▩', '▲►▼◄', '/-\\|']        
        #animation = choice(animations)
        animation = animations[-1]
        idx = 0
        prev_cmd = ''
        while Display.running: 
            if prev_cmd != Display.cmd and prev_cmd != '':
                print(prev_cmd, '✓')
                #animation = choice(animations)
                idx = 0
                
            if type(Display.cmd) == list:
                print(Display.cmd[0])
                Display.cmd = Display.cmd[1]
            if Display.cmd != '':
                print(Display.cmd, animation[idx], end="\r")
                idx = (idx+1) % len(animation)
            prev_cmd = Display.cmd
            time.sleep(Display.delay) 
            
    @staticmethod
    def endl():
        Display.cmd = ''
        
    @staticmethod
    def stop(exit = True):
        Display.cmd = ''
        time.sleep(2*Display.delay)
        Display.running = False
        print('All set!')
        if exit:
            sys.exit(0)
        
Display.init()

def get_file(name):
    return base_path + '/' + name

def run(cmd, cwd=None,show=False):
    if show:
        Display.msg(cmd)
    if type(cmd) == list:
        cmd = cmd[0]
    out = check_output(shlex.split(cmd), stderr=PIPE, cwd=cwd).decode('utf-8').splitlines()
    return out

class Sudo:
    def __init__(self,gui=False):
        print('Retrieving system state...')
        if os.uname()[1] == 'ecn-focal':
            self.passwd = 'ecn'.encode()
        else:
            self.passwd = None
            ask_passwd = True
            import getpass
            while ask_passwd:                    
                self.passwd = getpass.getpass('Enter admin password: ').encode()
                # check passwd
                proc = Popen(['sudo','-S','-l'],stdin=PIPE,stdout=PIPE,stderr=PIPE)
                out = proc.communicate(self.passwd)
                if 'incorrect' not in out[1].decode():
                    ask_passwd = False
                        
        self.run('apt update -qy')
                
    def run(self, cmd, cwd=None,show=True):
        
        if show:
            Display.msg(cmd, True)
        if type(cmd) == list:
            cmd = cmd[0]
        proc = Popen(['sudo','-S'] + shlex.split(cmd), stdin=PIPE, stderr=PIPE, stdout=PIPE if show else DEVNULL,cwd=cwd)
        proc.communicate(self.passwd)
        proc.wait()
                
    def apt_install(self, pkgs):
        
        if not len(pkgs):
            return
        
        # check ROS keys if needed
        need_ros1 = any(pkg.startswith(f'ros-{ros1}') for pkg in pkgs)
        need_ros2 = any(pkg.startswith(f'ros-{ros2}') for pkg in pkgs)
        if need_ros1 or need_ros2:                        
            
            refresh_src = False
            
            if not any('Open Robotics' in line for line in run('apt-key list')):
                self.run("sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key  -o /etc/apt/trusted.gpg.d/ros-archive-keyring.gpg")
                refresh_src = True
            
            if need_ros1 and not os.path.exists('/etc/apt/sources.list.d/ros-latest.list'):
                self.run(["sh -c 'echo \"deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main\" > /etc/apt/sources.list.d/ros-latest.list'", 'Getting ROS 1 keys'])
                refresh_src = True
                
            if need_ros2 and not os.path.exists('/etc/apt/sources.list.d/ros2-latest.list'):
                self.run(["sh -c 'echo \"deb http://packages.ros.org/ros2/ubuntu `lsb_release -cs` main\" > /etc/apt/sources.list.d/ros2-latest.list'", 'Getting ROS 2 keys'])
                refresh_src = True
                
            if refresh_src:
                self.run('apt update -qy')
                
        self.run(['apt install -qy ' + ' '.join(pkgs), 'Installing packages'])
    
    def apt_remove(self,pkgs,kept):
        
        if not len(pkgs):
            return
            
        # simulate removal of each element
        actually_removed = []
        Display.msg('Listing useless packages', True)
        for pkg in pkgs:
            out = run(f'apt remove {pkg} --dry-run',show=False)
            for line in out:
                if line.startswith('Remv'):
                    other = line.split('[')[0][4:].strip()
                    if other in kept:
                        break
            else:
                actually_removed.append(pkg)
        
        if len(actually_removed):
            self.run(['apt purge -qy ' + ' '.join(actually_removed), 'Removing packages'])
            self.run('apt autoremove --purge -qy')
        
    def deb_install(self, url):
        dst = os.path.basename(url).split('=')[-1]
        run(f'wget "{url}" -O /tmp/{dst}')
        self.run(f'dpkg -i /tmp/{dst}')
        
poweroff = False

if '--poweroff' in sys.argv:
    r = input('Will poweroff computer after update [y/N] ')
    if r in ('Y','y'):
        poweroff = True
        
sudo = Sudo()
                    
def src_type(src, dst):
    return '_'.join([src,dst]).upper().strip('_')

class Enum(object):
    def __init__(self, *keys):
        self.__dict__.update(dict([(key.upper(), i) for i,key in enumerate(keys)]))
    def values(self):
        return self.__dict__.values()

Action = Enum('Remove', 'Keep', 'Install')
Source = Enum(*([src_type(src,dst) for src in ('apt','deb','git') for dst in ('', 'ros', 'ros2')]))
Status = Enum('Absent', 'Old', 'Installed')

actions = {Action.REMOVE: 'Remove', Action.KEEP: 'Keep as it is', Action.INSTALL: 'Install / update'}
status = {Status.ABSENT: 'Not installed', Status.OLD: 'Needs update', Status.INSTALLED: 'Up-to-date'}

special_modules = {'cleanup': Action.REMOVE, 'base': Action.INSTALL}

class Depend:
    
    packages = {}
    packages_old = []
                
    def __init__(self, pkg, src):
        
        self.pkg, self.src = Depend.resolve(pkg, src)
        
        self.status = self.check()
        self.result = Action.KEEP
            
        self.pending = {}
        self.cmake = ''
        
    def cmake_flag(self, flag):
        if self.cmake  == '':
            self.cmake = flag
        
    def need_install(self):
        return self.result == Action.INSTALL and self.status != Status.INSTALLED
    
    def need_remove(self):
        return self.result == Action.REMOVE and self.status != Status.ABSENT
        
    def keep_apt(self):
        return self.status != Status.ABSENT and self.result != Action.REMOVE and self.src == Source.APT           
    
    @staticmethod
    def init_folders(folder):
        Depend.folders = {Source.GIT: folder, 
               Source.GIT_ROS: folder+'/ros1', 
               Source.GIT_ROS2: folder+'/ros2'}
        
    @staticmethod
    def resolve(pkg, src):
        if src == Source.APT_ROS:
            return f'ros-{ros1}-{pkg}', Source.APT
        elif src == Source.APT_ROS2:
            return f'ros-{ros2}-{pkg}', Source.APT
        elif src in (Source.GIT_ROS, Source.GIT_ROS2, Source.GIT):
            if not pkg.startswith('http'):
                owner,repo = pkg.split(':',1)
                pkg = f'https://github.com/{owner}/{repo}'
        return pkg, src
        
    def matches(self, pkg, src):
        pkg, src = Depend.resolve(pkg, src)
        return pkg == self.pkg and src == self.src
        
    def configure(self, module, action):
        self.pending[module] = action
        self.result = max(self.pending.values())
        #print(f'{module} wants {self.pkg} to be: {actions[action]} -> {actions[self.result]}')
        #print('', self.pending)
        
    def pending_status(self):
        if self.result == Action.INSTALL:
            return Status.INSTALLED
        elif self.result == Action.REMOVE:
            return Status.ABSENT
        
        # Action.KEEP
        return self.status        
        
    def abs_folder(self):
        pkg = self.pkg.split(':')[1]
        return self.parent_folder() + '/' + os.path.splitext(os.path.basename(pkg))[0]
    
    def parent_folder(self):
        return Depend.folders[self.src] + ('' if self.src == Source.GIT else '/src')
        
    def check(self):       
        
        if not Depend.packages:
            out = run('apt list --installed',show=True)
            for line in out:
                if '/' not in line:
                    continue                
                pkg,ver,_,status = line.split(' ',3)
                pkg = pkg[:pkg.find('/')]
                Depend.packages[pkg] = ver

                if 'upgradeable to:' in status:
                    Depend.packages_old.append(pkg)
        
        if self.src == Source.APT:
            if self.pkg not in Depend.packages:
                return Status.ABSENT
            if self.pkg in Depend.packages_old:
                return Status.OLD
            return Status.INSTALLED
        
        if self.src == Source.DEB:  # package_X.X.X*.deb
            pkg,ver_ext = os.path.basename(self.pkg.split('=')[-1]).split('_',1)
            
            ver = re.search('[0-9]+\\.[0-9]+\\.[0-9]+(-[0-9])?',ver_ext)
            ver = ver_ext[ver.start():ver.end()]
            if pkg in Depend.packages:
                return Status.INSTALLED if Depend.packages[pkg] >= ver else Status.OLD
            return Status.ABSENT
        
        base_dir = self.abs_folder()
                
        if not os.path.exists(base_dir):
            return Status.ABSENT
                
        # check GIT wrt upstream
        run('git fetch',cwd=base_dir)
        git_status = run('git status', cwd=base_dir)[1]
        
        if 'behind' not in git_status and '-g' not in sys.argv:
            return Status.INSTALLED
        return Status.OLD        
    
    def update(self):
        
        if not self.need_install():
            return None
                
        if self.src == Source.APT:
            return self.src
        
        if self.src == Source.DEB:
            sudo.deb_install(self.pkg)
            return self.src
        
        # git-based, may also be inside ros1 or ros2 local ws
        root = self.parent_folder()
        
        if not os.path.exists(root):
            sudo.run(f'mkdir -p {root}')
        
        perms = run(f'stat {Depend.folders[Source.GIT]}')
        for line in perms:
            if line.startswith('Access'):
                if 'root' in line:
                    user = os.environ['USER']
                    sudo.run(f'chown {user} {Depend.folders[Source.GIT]} -R',show=False)
                break
            
        base_dir = self.abs_folder()
        if os.path.exists(base_dir):
            
            # uninstall previous files in case new commit removes any
            self.uninstall()
            
            # update repo
            Display.msg('Refreshing repo ' + base_dir,True)
            run('git pull',cwd=base_dir,show=False)
        else:
            # clone
            if self.pkg.count(':') == 2:
                # branch is specified
                url,branch = self.pkg.rsplit(':',1)
                run(f'git clone {url} -b {branch}', cwd=root,show=True)
            else:
                run('git clone ' + self.pkg, cwd=root,show=True)
            
        # install if not ROS
        if self.src == Source.GIT and os.path.exists(base_dir + '/CMakeLists.txt'):
            build_dir = base_dir + '/build'
            Display.msg(f'Compiling + installing {base_dir}')
            run(f'mkdir -p {build_dir}',show=False)
            run('cmake {} ..'.format(self.cmake),cwd=build_dir,show=False)            
            sudo.run('make install -j4', cwd=build_dir, show=False)
            
        return self.src
    
    def uninstall(self):
        
        base_dir = self.abs_folder()
        pkgs = []
        
        def remove_if_here(path):
            if os.path.exists(path):
                sudo.run(f'rm -rf {path}',show=False)
        
        installed_files = []        
        if self.src == Source.GIT:            
            manifest = base_dir + '/build/install_manifest.txt'
        
            if os.path.exists(manifest):
                # purge installed files
                with open(manifest) as f:
                    installed_files = f.read().splitlines()
                    
        else:   # ROS1 / ROS2
            # find all packages defined in this clone
            for root, subdirs, files in os.walk(base_dir):
                if 'package.xml' in files:
                    with open(root + '/package.xml') as f:
                        xml = f.read()
                        pkgs.append(xml[xml.find('<name>')+6:xml.find('</name>')].strip())
                    subdirs = []
                    
            if self.src == Source.GIT_ROS:
                for pkg in pkgs:
                    manifest = f'{Depend.folders[self.src]}/build/{pkg}/install_manifest.txt'
                    if os.path.exists(manifest):
                        with open(manifest) as f:
                            raw_manifest = f.read().splitlines()
                            installed_files += [f for f in raw_manifest if not os.path.dirname(f).endswith('/install')]
                        
            elif self.src == Source.GIT_ROS2:
                # just remove install folder
                for pkg in pkgs:
                    remove_if_here(f'{Depend.folders[self.src]}/install/{pkg}')
        
        # clean files from manifest
        folders = set()
        for f in installed_files:
            folder = f
            while folder not in ('/',''):
                folder = os.path.dirname(folder)
                if os.path.exists(folder):
                    folders.add(folder)
                    
            remove_if_here(f)
            
        # cleanup created directories
        empty_folders = True
        while empty_folders:
            empty_folders = [folder for folder in folders if not os.listdir(folder)]
            for folder in empty_folders:
                remove_if_here(folder)
                folders.remove(folder)
        
        return pkgs
                        
    def remove(self):
        
        if not self.need_remove():
            return None
        
        # deb packages are removed in a single call to apt
        if self.src == Source.APT:
            return self.pkg
        if self.src == Source.DEB:
            return os.path.basename(self.pkg.split('=')[-1]).split('_',1)[0]
        
        # git packages are removed right here        
        ros_pkgs = self.uninstall()
        
        # also remove build artefacts and source
        base_dir = self.abs_folder()                                        
                        
        if self.src in (Source.GIT_ROS, Source.GIT_ROS2):
                    
            if os.path.exists(f'{Depend.folders[self.src]}/.catkin_tools'):
                # catkin-based clean if used
                for pkg in ros_pkgs:
                    run(f'catkin clean {pkg}', cwd=Depend.folders[self.src])
                    
            # colcon-based clean
            for root in ('build','log','logs'):
                for pkg in ros_pkgs:
                    folder = f'{Depend.folders[self.src]}/{root}/{pkg}'
                    if os.path.exists(folder):
                        rmtree(folder)
                        
        # destroy git clone, has to use sudo because of build artifacts during install
        sudo.run(f'rm -rf {base_dir}',show=False)
            
        return None

class Module:
    
    depends = []
    
    def add_depend(self, pkg, src):
        
        for dep in Module.depends:
            if dep.matches(pkg, src):
                break
        else:
            dep = Depend(pkg, src)
            Module.depends.append(dep)
        
        self.add_depends(dep)
        if 'description' in self.config:
            dep.configure(self.name, Action.KEEP)
        if 'cmake' in self.config:
            dep.cmake_flag(self.config['cmake'])

    def __init__(self, name, config):
        self.name = name
        
        for dep in ('ros','ros2'):
            if name != dep and dep in config:
                if 'mod' not in config:
                    config['mod'] = []
                config['mod'].append(dep)
        
        self.config = config

        self.parse_depends()
        
        if name in special_modules:
            self.configure(special_modules[name])
        
    def check_status(self, pending = False):
        
        if pending:
            self.status = min(dep.pending_status() for dep in self.all_deps())
            return self.status      
        
        self.status = min(dep.status for dep in self.all_deps())
        
        autoclean = '-r' in sys.argv
        if 'description' in self.config:
            # auto clean deps if module is not here
            self.configure(Action.REMOVE if (self.status == Status.ABSENT and autoclean) else Action.KEEP)
        
    def sync_depends(self, modules):
                
        if 'mod' in self.config:
            for name in self.config.pop('mod'):
                for level,deps in modules[name].sync_depends(modules).items():
                    self.add_depends(deps, level+1)
            self.check_status()       
        return self.deps
    
    def all_deps(self):
        return [dep for deps in self.deps.values() for dep in deps]

    def add_depends(self, deps, level = 0):
        
        if level not in self.deps:
            self.deps[level] = set()
        if isinstance(deps, set):
            for dep in deps:
                self.deps[level].add(dep)
        else:
            self.deps[level].add(deps)
        
    def parse_depends(self):
        
        self.deps = {}
        
        for key in Source.__dict__:
            src = key.lower().split('_')
            if len(src) == 2:
                src,dst = src
                if dst not in self.config:
                    continue
                sub = self.config[dst]
            else:
                src,dst = src[0], ''
                sub = self.config
                
            if src not in sub:
                continue            
            
            for pkg in sub[src]:
                self.add_depend(pkg, getattr(Source, key))
        
    def description(self):
        return self.name.upper() + ' (' + self.config['description'] + ')'
    
    def configure(self, action):
        if self.name in special_modules:
            action = special_modules[self.name]     
        for dep in self.all_deps():
            dep.configure(self.name, action)
            
with open(get_file('modules.yaml')) as f:
    info = yaml.safe_load(f)
    
Depend.init_folders(info['lib_folder'] if 'lib_folder' in info else '/opt/local_ws')
modules = dict((name, Module(name, config)) for name, config in info.items() if isinstance(config, dict))
groups = dict(((name, config) for name, config in info.items() if isinstance(config, list)))

for module in modules.values():
    module.sync_depends(modules)
    module.check_status()

def perform_update(action = None, poweroff=False):
    '''
    Final action
    '''
    if action is not None:
        for m in modules.values():
            if 'description' in m.config:
                m.configure(action)
            
    if sudo.passwd is None:
        return
                        
    # remove old ones
    pkgs = [dep.remove() for dep in Module.depends]
    kept = [dep.pkg for dep in Module.depends if dep.keep_apt()]
    sudo.apt_remove([pkg for pkg in pkgs if pkg], kept)
                
    # filter by source APT > DEB
    to_install = dict((src, [dep for dep in Module.depends if dep.need_install() and dep.src == src]) for src in Source.values())
    
    # apt-based new packages
    pkgs = [dep.pkg for dep in to_install[Source.APT]]
    if len(pkgs):
        sudo.apt_install(pkgs)
    
    # global ones
    if len(Depend.packages_old):
        sudo.run('apt upgrade -qy')
        sudo.run('apt autoremove --purge -qy')
    
    # deb-based
    updated = [dep.update() for dep in to_install[Source.DEB]]
    if Source.DEB in updated:
        sudo.run('apt install -qy --fix-broken --fix-missing')
            
    # git-based
    for dep in to_install[Source.GIT]:
        dep.update()
        
    # ros ws
    need_chmod = False
    updated = [dep.update() for dep in to_install[Source.GIT_ROS] + to_install[Source.GIT_ROS2]]
    # recompile ros1ws    
    if Source.GIT_ROS in updated or ('-f' in sys.argv and os.path.exists(Depend.folders[Source.GIT_ROS])):
        if not os.path.exists(f'{Depend.folders[Source.GIT_ROS]}/.catkin_tools'):
            # purge colcon install
            for folder in ('build','install','devel','log'):
                if os.path.exists(f'{Depend.folders[Source.GIT_ROS]}/{folder}'):
                    rmtree(f'{Depend.folders[Source.GIT_ROS]}/{folder}')
                    
            run(f'catkin config --init --extend /opt/ros/{ros1} --install -DCATKIN_ENABLE_TESTING=False --make-args -Wno-dev --cmake-args -DCMAKE_BUILD_TYPE=Release', cwd=Depend.folders[Source.GIT_ROS])
        run([f'catkin build  --continue-on-failure', f'Compiling ROS 1 auxiliary workspace @ {Depend.folders[Source.GIT_ROS]}'], cwd=Depend.folders[Source.GIT_ROS], show=True)
        need_chmod = True

    # recompile ros2ws
    if Source.GIT_ROS2 in updated or ('-f' in sys.argv and os.path.exists(Depend.folders[Source.GIT_ROS2])):
        run([f'bash -c -i "source /opt/ros/{ros2}/setup.bash && colcon build --symlink-install --continue-on-error"',f'Compiling ROS 2 auxiliary workspace @ {Depend.folders[Source.GIT_ROS2]}'], cwd=Depend.folders[Source.GIT_ROS2], show=True)
        need_chmod = True
    
    if need_chmod:
        sudo.run([f'chmod a+rX {Depend.folders[Source.GIT]} -R', 'Setting permissions'])
    
    if os.path.exists('/opt/coppeliaSim'):
        sudo.run('chmod a+rwX -R /opt/coppeliaSim',show=False)
    
    # poweroff only if no one else is connected
    if poweroff and all(user == Display.user for user in run('users')[0].split()):
        Display.stop(False)
        sudo.run('poweroff')
    else:
        Display.stop()
    
def Font(size = 10):
    return QFont("Helvetica", size, QFont.Bold)


class UpdaterGUI(QWidget):
    
    def __init__(self):
        super().__init__()
                
        self.setWindowIcon(QIcon(get_file('images/ecn.png')))
        self.setWindowTitle('Virtual Machine updater')                           
                
        # build GUI        
        sliderUpdateTrigger = Signal()
        layout = QVBoxLayout(self)
        
        gridlayout = QGridLayout()
        font = Font()
        
        # top bar = groups
        groups_layout = QHBoxLayout()
        label = QLabel('Groups', self)
        label.setFont(Font(12))
        groups_layout.addWidget(label)
                
        for group in groups:
                        
            groups_layout.addSpacing(10)
            group_layout = QHBoxLayout()
            groups[group] = {'cb': QCheckBox(self), 'modules': groups[group]}
            groups[group]['cb'].setText(group)
            groups[group]['cb'].setFont(font)
            groups_layout.addWidget(groups[group]['cb'])
            groups[group]['cb'].clicked.connect(self.group_update)
                        
            
        layout.addLayout(groups_layout)  
        layout.addSpacing(10)
        
        mod_layout = QGridLayout()
        spacer = QSpacerItem(10, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        for i,module in enumerate(modules.values()):
            if 'description' in module.config:
                mod_layout.addItem(spacer, i, 0)
                label = QLabel(module.description(), self)
                label.setFont(font)
                mod_layout.addWidget(label, i, 1)
                mod_layout.addItem(spacer, i, 2)
                
                label = QLabel(status[module.status], self)
                label.setFont(font)            
                mod_layout.addWidget(label, i, 3)
                
                module.menu = QComboBox(self)
                for choice in actions.values():
                    module.menu.addItem(choice)
                if module.status == Status.OLD:
                    module.menu.setCurrentIndex(Action.INSTALL)
                else:
                    module.menu.setCurrentIndex(Action.KEEP)
                module.menu.currentIndexChanged.connect(module.configure)
                    
                module.menu.setFont(font)
                mod_layout.addWidget(module.menu, i, 4)
                mod_layout.addItem(spacer, i, 5)
                
        for group in groups.values():
            if all(modules[name].status != Status.ABSENT for name in group['modules']):
                group['cb'].setChecked(True)
                            
        layout.addLayout(mod_layout)        
        layout.addSpacing(10)
        
        confirm_layout = QHBoxLayout()
        ok_btn = QPushButton('Perform update')
        ok_btn.setFont(font)
        ok_btn.clicked.connect(self.perform)
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setFont(font)
        cancel_btn.clicked.connect(self.close)        
        confirm_layout.addWidget(ok_btn)
        confirm_layout.addWidget(cancel_btn)
        layout.addLayout(confirm_layout)
                                
        self.show()
        
    def perform(self, event):
        perform_update()
        self.close()
        
    def group_update(self, clicked):
        module_checked = dict((name,False) for group in groups.values() for name in group['modules'])
        #print([(m, c) for m,c in module_checked.items()])
        for name,group in groups.items():
            
            for module in group['modules']:
                module_checked[module] = module_checked[module] or group['cb'].isChecked()
            #print(name, group['cb'].isChecked())
            #print(module_checked)
        
        for name,checked in module_checked.items():
            module = modules[name]
            if checked and module.status != Status.INSTALLED:
                module.menu.setCurrentIndex(Action.INSTALL)
            else:
                module.menu.setCurrentIndex(Action.KEEP)
    
if '-t' in sys.argv:
    # to test things
    Display.stop()    
    
if '-u' in sys.argv:
    to_update = [mod for mod in modules if mod in sys.argv]

    if len(to_update) == 0:
        # update all existing ones
        to_update = [mod for mod in modules if modules[mod].status != Status.ABSENT]
                
    for mod in to_update:
        modules[mod].configure(Action.INSTALL)
            
    perform_update(poweroff=poweroff)
        
if '-a' in sys.argv:
    # install / update all modules
    perform_update(Action.INSTALL,poweroff=poweroff)

sys._excepthook = sys.excepthook 
def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback) 
    sys.exit(1) 
sys.excepthook = exception_hook 

Display.endl()
app = QApplication(sys.argv)
gui = UpdaterGUI()

app.exec_()
Display.stop()
