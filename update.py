#!/usr/bin/env python3
import yaml
import sys
import os
import shlex
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout,QHBoxLayout,QGridLayout, QLabel, QPushButton, QCheckBox, QComboBox, QSpacerItem, QSizePolicy, QInputDialog, QLineEdit
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtGui import QFont, QIcon
from subprocess import check_output, PIPE, Popen, DEVNULL

base_path = os.path.dirname(os.path.abspath(__file__))

ros1 = 'noetic'
ros2 = 'foxy'

def display(s, sudo = False):
    if sudo:
        print('\033[93m [sudo]\t' + '\033[1;37;0m ' + s)
    else:
        print('\033[96m ['+os.environ['USER'] +']\t' + '\033[1;37;0m ' + s)

def get_file(name):
    return base_path + '/' + name

def run(cmd, cwd=None,show=False):
    if show:
        display(cmd)
    return check_output(shlex.split(cmd), stderr=PIPE, cwd=cwd).decode('utf-8').splitlines()

class Sudo:
    def __init__(self,gui=False):
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
            display(cmd,True)
        proc = Popen(['sudo','-S'] + shlex.split(cmd), stdin=PIPE, stderr=PIPE,cwd=cwd)
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
                self.run("curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -")
                refresh_src = True
            
            if need_ros1 and not os.path.exists('/etc/apt/sources.list.d/ros-latest.list'):
                self.run("sh -c 'echo \"deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main\" > /etc/apt/sources.list.d/ros-latest.list'")
                refresh_src = True
                
            if need_ros2 and not os.path.exists('/etc/apt/sources.list.d/ros2-latest.list'):
                self.run("sh -c 'echo \"deb http://packages.ros.org/ros2/ubuntu `lsb_release -cs` main\" > /etc/apt/sources.list.d/ros2-latest.list'")
                refresh_src = True
                
            if refresh_src:
                self.run('apt update -qy')
                
        self.run('apt install -qy ' + ' '.join(pkgs))
        
    def deb_install(self, url):
        dst = os.path.basename(url)
        run(f'wget {url} -P /tmp')
        self.run(f'dpkg -i /tmp/{dst}')
        self.run('apt install --fix-missing')
        
sudo = Sudo()
                    
def src_type(src, dst):
    return '_'.join([src,dst]).upper().strip('_')

class Enum(object):
    def __init__(self, *keys):
        self.__dict__.update(dict([(key.upper(), i) for i,key in enumerate(keys)]))

Action = Enum('Remove', 'Keep', 'Install')
Source = Enum(*(['DEB'] + [src_type(src,dst) for src in ('apt','git') for dst in ('', 'ros', 'ros2')]))
Status = Enum('Absent', 'Old', 'Installed')

actions = {Action.REMOVE: 'Remove', Action.KEEP: 'Keep as it is', Action.INSTALL: 'Install / update'}
status = {Status.ABSENT: 'Not installed', Status.OLD: 'Needs update', Status.INSTALLED: 'Up-to-date'}

class Element:
    
    packages = {}
    packages_old = []
                
    def __init__(self, pkg, src):
        
        self.pkg, self.src = Element.resolve(pkg, src)
        self.status = self.check()
        self.pending = {}
        
        self.cmake = ''
        
    def cmake_flag(self, flag):
        if self.cmake  == '':
            self.cmake = flag
        
    def need_install(self):
        return self.result == Action.INSTALL and self.status != Status.INSTALLED
    
    @staticmethod
    def init_folders(folder):
        Element.folders = {Source.GIT: folder, 
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
        pkg, src = Element.resolve(pkg, src)
        return pkg == self.pkg and src == self.src
        
    def configure(self, module, action):
        self.pending[module] = action
        self.result = max(self.pending.values())
        #print(f'{module} wants {self.pkg} to be: {actions[action]} -> {actions[self.result]}')
        #print('', self.pending)
        
    def abs_folder(self):
        pkg = self.pkg.split(':')[1]
        return self.parent_folder() + '/' + os.path.splitext(os.path.basename(pkg))[0]
    
    def parent_folder(self):
        return Element.folders[self.src] + ('' if self.src == Source.GIT else '/src')
        
    def check(self):
        
        if not Element.packages:
            out = run('apt list --installed',show=True)
            for line in out:
                if '/' not in line:
                    continue
                line = line.split()
                pkg = line[0][:line[0].find('/')]
                ver = line[1]
                Element.packages[pkg] = ver
            
            out = run('apt list --upgradeable',show=True)
            Element.packages_old = [line.split('/')[0] for line in out if '/' in line]
        
        if self.src == Source.APT:
            if self.pkg not in Element.packages:
                return Status.ABSENT
            if self.pkg in Element.packages_old:
                return Status.OLD
            return Status.INSTALLED
        
        if self.src == Source.DEB:  # package_X.X.X.deb
            pkg,ver = os.path.basename(self.pkg).split('_')
            ver = ver[:ver.rfind('.')]
            if pkg in Element.packages:
                return Status.INSTALLED if Element.packages[pkg] == ver else Status.OLD
            return Status.ABSENT
        
        base_dir = self.abs_folder()
                
        if not os.path.exists(base_dir):
            return Status.ABSENT
                
        # check GIT version
        upstream = run('git status', cwd=base_dir)[1].split("'")[1]
                
        diff = run(f'git rev-list HEAD...{upstream} --count', cwd=base_dir)[0]
        if diff == '0':
            return Status.INSTALLED
        return Status.OLD
    
    def update_from(self, sudo):
        
        # TODO check if should be removed
        if self.status == Status.INSTALLED and '-f' not in sys.argv:
            return None
        
        if self.src == Source.APT:
            return Source.APT
        
        if self.result == Action.KEEP:
            return None
        
        if self.src == Source.DEB:
            if self.need_install():
                sudo.deb_install(self.pkg)
            elif self.status != Status.ABSENT and self.result == Action.REMOVE:
                pkg = os.path.basename(self.pkg).split('_')[0]
                sudo.run(f'apt purge {pkg}')
            return None
        
        # git-based, may also be inside ros1 or ros2 local ws
        root = self.parent_folder()
        
        if not os.path.exists(root):
            sudo.run(f'mkdir -p {root}')
        
        perms = run(f'stat {Element.folders[Source.GIT]}')
        for line in perms:
            if line.startswith('Access'):
                if 'root' in line:
                    user = os.environ['USER']
                    sudo.run(f'chown {user} {Element.folders[Source.GIT]} -R',show=False)
                break
            
        base_dir = self.abs_folder()
        if os.path.exists(base_dir):
            # update repo
            print('Updating ' + base_dir)
            run('git pull', cwd=base_dir)
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
            run(f'mkdir -p {build_dir}')
            run('cmake {} ..'.format(self.cmake),cwd=build_dir)
            sudo.run('make install', cwd=build_dir)            
            
        return self.src
                        
    def remove(self):
        # later...
        1 

class Module:
    
    depends = []
    
    def add_depend(self, pkg, src):
        
        for dep in Module.depends:
            if dep.matches(pkg, src):
                break
        else:
            dep = Element(pkg, src)
            Module.depends.append(dep)
        
        self.add_depends(dep)
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
        if 'update' not in self.config or '-f' in sys.argv:
            self.config['update'] = True

        self.parse_depends()        
        
    def check_status(self):
        if 'description' in self.config:
            self.configure(Action.KEEP)
        self.status = min(dep.status for dep in self.all_deps())

        if self.status != Status.ABSENT and not self.config['update']:
            self.status = Status.INSTALLED   
        
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
        for dep in self.all_deps():
            dep.configure(self.name, action)
            
with open(get_file('modules.yaml')) as f:
    info = yaml.safe_load(f)
    
Element.init_folders(info['lib_folder'] if 'lib_folder' in info else '/opt/local_ws')
modules = dict((name, Module(name, config)) for name, config in info.items() if isinstance(config, dict))
groups = dict(((name, config) for name, config in info.items() if isinstance(config, list)))

for module in modules.values():
    module.sync_depends(modules)
    module.check_status()

def perform_update(action = None):
    '''
    Final action
    '''
    if action is not None:
        for m in modules.values():
            m.configure(action)
            
    if sudo.passwd is None:
        return    
                
    # apt-based new packages    
    pkgs = [dep.pkg for dep in Module.depends if dep.src==Source.APT and dep.need_install()]
    if len(pkgs):
        sudo.apt_install(pkgs)
    
    # global ones    
    sudo.run('apt upgrade -qy')
    sudo.run('apt autoremove --purge -qy')
    
    # other packages can deal with themselves
    ret = []
    for dep in Module.depends:
        if dep.need_install():
            ret.append(dep.update_from(sudo))
    
    need_chmod = False
    # recompile ros1ws
    if Source.GIT_ROS in ret or '-f' in sys.argv:
        print('Compiling ROS 1 local workspace...')
        if not os.path.exists(f'{Element.folders[Source.GIT_ROS]}/.catkin_tools'):
            run(f'catkin config --init --extend /opt/ros/{ros1} --install -DCATKIN_ENABLE_TESTING=False --make-args -Wno-dev --cmake-args -DCMAKE_BUILD_TYPE=Release', cwd=Element.folders[Source.GIT_ROS])
        run(f'catkin build  --continue-on-failure', cwd=Element.folders[Source.GIT_ROS],show=True)
        need_chmod = True
            
    # recompile ros2ws
    if Source.GIT_ROS2 in ret or '-f' in sys.argv:
        print('Compiling ROS 2 local workspace...')
        run(f'bash -c -i "source /opt/ros/{ros2}/setup.bash && colcon build --symlink-install --continue-on-error"', cwd=Element.folders[Source.GIT_ROS2],show=True)
        need_chmod = True
    
    if need_chmod:
        sudo.run(f'chmod a+rX {Element.folders[Source.GIT]} -R',show=False)
    sudo.run('ldconfig',show=False)
    
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
    sys.exit(0)
    
if '-u' in sys.argv:    
    if sys.argv[-1] == '-u':
        perform_update(Action.KEEP)
    else:
        for key in sys.argv:
            if key in modules:
                modules[key].configure(Action.INSTALL)
        perform_update()
    sys.exit(0)
        
if '-a' in sys.argv:
    perform_update(Action.INSTALL)
    sys.exit(0)

try:
    ## build GUI
    app = QApplication(sys.argv)
    gui = UpdaterGUI()

    sys.exit(app.exec_())
except:
    pass
