#!/usr/bin/env python3
import yaml
import sys
import os
import shlex
import time
from shutil import rmtree, copytree
from threading import Thread
import re
from subprocess import check_output, PIPE, Popen, DEVNULL, CalledProcessError
import argparse

base_path = os.path.dirname(os.path.abspath(__file__))

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.description = 'Updater for ECN / ROS virtual machine.'

parser.add_argument('-u', metavar='module', type=str, nargs='+', help='Which modules to upgrade (all installed, if empty)', default=())
parser.add_argument('-n', '--no_upgrade', action='store_true', default=False, help='Does not perform apt upgrade')
parser.add_argument('-t', '--test', action='store_true', default=False, help='Run in interactive mode (from a Python console)')
parser.add_argument('-a', '--all', action='store_true', default=False, help='Install all available modules')
parser.add_argument('-c', '--clean', action='store_true', default=False, help='Clean listed modules that are not required')
parser.add_argument('-f', '--force_compile', action='store_true', default=False, help='Force recompilation of ROS workspaces')
parser.add_argument('-g', '--force_git', action='store_true', default=False, help='Force git pull on suitable folders')
parser.add_argument('--chmod', action='store_true', default=False, help='Force chmod on installed folder')
parser.add_argument('--nosrc', action='store_true', default=False, help='Ignore source dependencies')
parser.add_argument('--nopip', action='store_true', default=False, help='Ignore pip dependencies')
parser.add_argument('-p', '--poweroff', action='store_true', default=False, help='Poweroff after installation / upgrade')

# add empty space after -u if no modules
if '-u' in sys.argv:
    sys.argv.insert(sys.argv.index('-u')+1, '')

args = parser.parse_args()

# check we do not run as root
if os.geteuid() == 0 or 'SUDO_UID' in os.environ:
    print('\n   Do not run this script as root or sudo')
    import sys
    sys.exit(0)


def fuse(src1: dict, src2: dict):
    keys = set(src1.keys()).union(src2.keys())
    dst = {}

    for key in keys:
        if key not in src2:
            dst[key] = src1[key]
        elif key not in src1:
            dst[key] = src2[key]
        elif isinstance(src1[key], str):
            dst[key] = src1[key]
        elif isinstance(src1[key], list):
            dst[key] = src1[key] + src2[key]
        else:
            dst[key] = fuse(src1[key], src2[key])

    return dst


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
        if isinstance(cmd, list):
            Display.cmd = [Display.to_msg(cmd[0],sudo), Display.to_msg(' -> ' + cmd[1],sudo)]
        else:
            Display.cmd = Display.to_msg(cmd, sudo)

    @staticmethod
    def blit():

        animations = ['◜◝◞◟','◣◤◥◢','▤▥▦▧▨▩', '▲►▼◄', '/-\\|']
        done_smb = '..done'  # '✓'

        #  animation = choice(animations)
        animation = animations[-1]
        idx = 0
        prev_cmd = ''
        while Display.running:
            if prev_cmd != Display.cmd and prev_cmd != '':
                print(prev_cmd, done_smb)
                #  animation = choice(animations)
                idx = 0

            if isinstance(Display.cmd, list):
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
    if isinstance(cmd, list):
        cmd = cmd[0]
    try:
        return check_output(shlex.split(cmd), stderr=PIPE, cwd=cwd).decode('utf-8').splitlines()
    except CalledProcessError:
        return None


distro = run('lsb_release -cs')[0]
ros1 = run(f'grep ros1_workspaces skel/{distro}/.bashrc', cwd=base_path)[0]
ros1 = ros1.replace('/',' ').split()[3].strip('"')
ros2 = run(f'grep ros2_workspaces skel/{distro}/.bashrc', cwd=base_path)[0]
ros2 = ros2.replace('/',' ').split()[3].strip('"')
gz = run(f'grep GZ_VERSION skel/{distro}/.bashrc', cwd=base_path)[0].split('=')[1].strip()
GZ = 'IGNITION' if gz == 'fortress' else 'GZ'
using_ecn_vm = os.uname().nodename == 'ecn-'+distro


# handle external repositories
class ExternalRepo:
    def __init__(self, prefix, key_url, lst_file, url, branch = 'main'):
        self.prefix = prefix
        self.key_url = key_url
        self.key_file = '/etc/apt/trusted.gpg.d/' + os.path.basename(key_url)
        self.lst_file = '/etc/apt/sources.list.d/' + lst_file
        self.url = url
        self.branch = branch

    def needed_for(self, pkgs):
        return any([pkg.startswith(self.prefix) for pkg in pkgs])

    def lst_content(self):
        return f'deb [arch=$(dpkg --print-architecture) signed-by={self.key_file}] {self.url} {distro} {self.branch}'


# enable OSRF repos if needed
additional_repos = [
    ExternalRepo(f'ros-{ros2}', 'https://raw.githubusercontent.com/ros/rosdistro/master/ros.key',
                    'ros2-latest.list', 'http://packages.ros.org/ros2/ubuntu'),
    ExternalRepo('ignition-', 'https://packages.osrfoundation.org/gazebo.gpg',
                    'gazebo-latest.list', 'http://packages.osrfoundation.org/gazebo/ubuntu-stable'),
    ExternalRepo('gz-', 'https://packages.osrfoundation.org/gazebo.gpg',
                    'gazebo-latest.list', 'http://packages.osrfoundation.org/gazebo/ubuntu-stable'),
    ExternalRepo('robotpkg-', 'http://robotpkg.openrobots.org/packages/debian/robotpkg.asc',
                    'robotpkg.list', 'http://robotpkg.openrobots.org/packages/debian/pub',
                    'robotpkg')]
if distro <= 'focal':
    additional_repos.append(ExternalRepo(f'ros-{ros1}', 'https://raw.githubusercontent.com/ros/rosdistro/master/ros.key',
                            'ros-latest.list', 'http://packages.ros.org/ros/ubuntu'))


# after 4 years finally some custom hacks are needed
if using_ecn_vm:
    if run('grep foxy .bashrc', cwd=os.environ['HOME']):
        args.force_compile = True
    run(f'{base_path}/scripts/vm_update.sh')


class Sudo:
    def __init__(self,gui=False):
        print('Retrieving system state...')
        if using_ecn_vm:
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

        # need to update ROS GPG key file as of 1 June 2025
        ros_repos = [repo for repo in additional_repos if repo.prefix.startswith('ros-')]
        repo = ros_repos[0]

        if os.path.exists(repo.key_file):
            from datetime import datetime
            modified = datetime.fromtimestamp(os.path.getmtime(repo.key_file))
            key_update = datetime(2025, 5, 31)
            if modified < key_update:
                self.run(f'wget {repo.key_url} -O {repo.key_file}')
                # also update source files
                for repo in ros_repos:
                    self.run(f"sh -c 'echo \"{repo.lst_content()}\" > {repo.lst_file}'")
                    self.run(f'chmod 664 {repo.lst_file}')

        self.run('apt update -qy')

    def run(self, cmd, cwd=None,show=True):

        if show:
            Display.msg(cmd, True)
        if isinstance(cmd, list):
            cmd = cmd[0]
        proc = Popen(['sudo','-S'] + shlex.split(cmd), stdin=PIPE, stderr=PIPE, stdout=PIPE if show else DEVNULL,cwd=cwd)
        proc.communicate(self.passwd)
        proc.wait()

    def apt_install(self, pkgs):

        if not len(pkgs):
            return

        refresh_src = False

        for repo in additional_repos:

            if not repo.needed_for(pkgs):
                continue

            if repo.prefix == f'ros-{ros1}' and distro > 'focal':

                # trying to install ROS 1 packages on 22.04+
                print('ROS 1 is not available on Ubuntu 22.04 or later, current install needs ' + ' '.join(pkg for pkg in pkgs if pkg.startswith(repo.prefix)))
                sys.exit(0)

            if not os.path.exists(repo.key_file):
                self.run(f'wget {repo.key_url} -O {repo.key_file}')
                refresh_src = True

            if not os.path.exists(repo.lst_file):
                self.run(f"sh -c 'echo \"{repo.lst_content()}\" > {repo.lst_file}'")
                Display.msg(f'Adding new repo: {repo.url}', True)
                self.run(f'chmod 664 {repo.lst_file}')
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
            self.run(['apt purge -qy --autoremove ' + ' '.join(actually_removed), 'Removing packages'])

    def deb_install(self, url):

        if not url.startswith('http'):
            url = 'https://box.ec-nantes.fr/index.php/s/s7rbFwAeTqwoe6e/download?path=%2F&files=' + url

        dst = os.path.basename(url).split('=')[-1]
        run(f'wget "{url}" -O /tmp/{dst}')
        self.run(f'apt install -qy /tmp/{dst}')


poweroff = False

if args.poweroff:
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
Source = Enum(*([src_type(src,dst) for src in ('apt','pip','deb','git') for dst in ('', 'ros', 'ros2')] + ['script']))
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
        if self.cmake == '':
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
    def split_deb(src):
        pkg,ver_ext = os.path.basename(src.split('=')[-1]).split('_',1)
        pkg = pkg.split('[')[0]
        ver = re.search('[0-9]+\\.[0-9]+\\.[0-9]+(-[0-9]+)?',ver_ext)
        ver = ver_ext[ver.start():ver.end()]
        return pkg,ver

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
        elif src == Source.DEB:
            pkg = pkg.replace('[]', f'[{distro}]')
        elif src == Source.SCRIPT:
            for cand in (pkg, f'scripts/{pkg}', f'scripts/{pkg}.bash'):
                if os.path.exists(get_file(cand)):
                    pkg = get_file(cand)
                    break
        return pkg, src

    def matches(self, pkg, src):
        pkg, src = Depend.resolve(pkg, src)
        return pkg == self.pkg and src == self.src

    def configure(self, module, action):
        self.pending[module] = action
        self.result = max(self.pending.values())
        # print(f'{module} wants {self.pkg} to be: {actions[action]} -> {actions[self.result]}')
        # print('', self.pending)

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
                pkg,ver,_ = line.split(' ',2)
                pkg = pkg[:pkg.find('/')]
                Depend.packages[pkg] = ver

            out = run('apt list --upgradable')
            for line in out:
                if '/' not in line:
                    continue
                pkg,_ = line.split(' ',1)
                Depend.packages_old.append(pkg[:pkg.find('/')])
            Display.endl()

        if self.src == Source.PIP:
            try:
                out = run('pip3 show ' + self.pkg)
                return Status.INSTALLED if out else Status.ABSENT
            except CalledProcessError:
                return Status.ABSENT
            except FileNotFoundError:
                return Status.ABSENT

        if self.src == Source.APT:
            if self.pkg not in Depend.packages:
                return Status.ABSENT
            if self.pkg in Depend.packages_old:
                return Status.OLD
            return Status.INSTALLED

        if self.src == Source.DEB:  # package[distro]_X.X.X*.deb
            pkg,ver = Depend.split_deb(self.pkg)
            if pkg in Depend.packages:
                return Status.INSTALLED if Depend.packages[pkg] >= ver else Status.OLD
            return Status.ABSENT

        if self.src == Source.SCRIPT:
            # delegate to script
            result = run(self.pkg + ' -c')[0]
            return getattr(Status, result.upper())

        if args.nosrc:
            return Status.INSTALLED

        base_dir = self.abs_folder()

        if not os.path.exists(base_dir):
            return Status.ABSENT

        # check GIT wrt upstream
        run('git fetch',cwd=base_dir)
        git_status = run('git status', cwd=base_dir)
        if git_status is None:
            return Status.OLD

        if 'behind' not in git_status[1] and not args.force_git:
            return Status.INSTALLED
        return Status.OLD

    def update(self):

        if not self.need_install():
            return None

        if self.src == Source.PIP:
            try:
                sudo.run('pip3 install ' + self.pkg, show=True)
            except CalledProcessError:
                print('Re-run the process after pip3 was installed')
            return self.src

        if self.src == Source.APT:
            return self.src

        if self.src == Source.DEB:
            sudo.deb_install(self.pkg)
            return self.src

        if self.src == Source.SCRIPT:
            sudo.run(self.pkg + ' -i')
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
            Display.msg('Refreshing repo ' + base_dir)
            run('git pull --recurse-submodules', cwd=base_dir,show=False)
        else:
            # clone
            if self.pkg.count(':') == 2:
                # branch is specified
                url,branch = self.pkg.rsplit(':',1)
                # branch may be ros-specific
                branch = branch.replace('<distro>', distro)
                run(f'git clone --recursive {url} -b {branch}', cwd=root,show=True)
            else:
                run('git clone --recursive ' + self.pkg, cwd=root,show=True)

        # install if not ROS
        if self.src == Source.GIT and os.path.exists(base_dir + '/CMakeLists.txt'):
            build_dir = base_dir + '/build'
            if os.path.exists(build_dir):
                run(f' rm -rf {build_dir}', show=False)
            Display.msg(f'Compiling + installing {base_dir}')
            run(f'mkdir -p {build_dir}',show=False)
            run('cmake {} ..'.format(self.cmake),cwd=build_dir,show=False)
            sudo.run('make install -j4', cwd=build_dir, show=False)

        return self.src

    def uninstall(self):

        base_dir = self.abs_folder()
        pkgs = []

        if self.src == Source.SCRIPT:
            sudo.run(self.pkg + ' -r')
            return pkgs

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
                    subdirs[:] = []

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
            return Depend.split_deb(self.pkg)[0]

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
            for root in ('build','log','logs','install'):
                for pkg in ros_pkgs:
                    folder = f'{Depend.folders[self.src]}/{root}/{pkg}'
                    if os.path.exists(folder):
                        rmtree(folder)

        # destroy git clone, has to use sudo because of build artifacts during install
        sudo.run(f'rm -rf {base_dir}',show=False)

        return None


class Module:

    depends = []

    def build_depend(self, pkg, src):

        for dep in Module.depends:
            if dep.matches(pkg, src):
                break
        else:
            dep = Depend(pkg, src)
            Module.depends.append(dep)

        self.add_depend(dep)
        if 'description' in self.config:
            dep.configure(self.name, Action.KEEP)
        if 'cmake' in self.config:
            dep.cmake_flag(self.config['cmake'])

    def __init__(self, name, config):
        self.name = name

        for dep in ('ros','ros2'):
            if name != dep and dep in config:
                if 'mod' not in config:
                    config['mod'] = [dep]
                elif dep not in config['mod']:
                    config['mod'].append(dep)

        self.config = config

        if 'pip' in config and args.nopip:
            config.pop('pip')
            print(' ignoring pip dependencies')

        self.parse_depends()

        if name in special_modules:
            self.configure(special_modules[name])

    def is_default(self):
        return 'description' in self.config and self.status != Status.ABSENT

    def check_status(self, pending = False):

        if len(self.deps) == 0:
            self.status = Status.INSTALLED
            if pending:
                return self.status
        elif pending:
            self.status = min(dep.pending_status() for dep in self.deps)
            return self.status
        else:
            self.status = min(dep.status for dep in self.deps)

        if 'description' in self.config:
            # auto clean deps if module is not here
            self.configure(Action.REMOVE if (self.status == Status.ABSENT and args.clean) else Action.KEEP)

    def sync_depends(self, modules):

        try:
            if 'mod' in self.config:
                for name in self.config.pop('mod'):
                    deps = modules[name].sync_depends(modules)
                    self.add_depends(deps)
                self.check_status()
        except KeyError as err:
            if self.name == 'cleanup':
                print('Invalid dependency in cleanup: ', err)
            else:
                print('While parsing dependencies of',self.name)
                raise err

        return self.deps

    # def all_deps(self):
    #     return [dep for deps in self.deps.values() for dep in deps]

    def add_depend(self, dep):
        self.deps.add(dep)

    def add_depends(self, deps):
        for dep in deps:
            self.deps.add(dep)

    def parse_depends(self):

        self.deps = set()

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
                self.build_depend(pkg, getattr(Source, key))

    def description(self):
        return self.name.upper() + ' (' + self.config['description'] + ')'

    def configure(self, action):
        if self.name in special_modules:
            action = special_modules[self.name]
        for dep in self.deps:
            dep.configure(self.name, action)


# read global + distro-specific modules
info = fuse(yaml.safe_load(open(get_file('modules.yaml'))),
            yaml.safe_load(open(get_file(f'modules-{distro}.yaml'))))

# keys with comma are double-keys
keys = list(info.keys())
for key in keys:
    if ',' not in key:
        continue
    detail = info.pop(key)
    for mod in key.split(','):
        info[mod.strip()] = dict(detail)

# erase disabled modules
disable = []
if 'disable' in info:
    disabled = info['disable']
    info.pop('disable')

groups = [key for key in info if isinstance(info[key], list) and 'ignore' not in key]

for mod in disable:
    if mod in info:
        info.pop(mod)
    for group in groups:
        if mod in info[group]:
            info[group].pop(mod)

ignore = info['vm_ignore'] if 'vm_ignore' in info and using_ecn_vm else []

Depend.init_folders(info['lib_folder'] if 'lib_folder' in info else '/opt/ecn')
modules = dict((name, Module(name, config)) for name, config in info.items() if isinstance(config, dict))
groups = dict((group, info[group]) for group in groups)

for module in modules.values():
    module.sync_depends(modules)
    module.check_status()


def extract_cmake_names(path):

    def project_name(line):
        try:
            line = line.lower().split('#')[0]
            if 'project' in line:
                start,end = line.index('(')+1, line.index(')')
                return line[start:end].split()[0]
        except ValueError:
            pass
        return None

    projects = {}

    for root, dirs, files in os.walk(path):
        if 'CMakeLists.txt' in files:

            with open(f'{root}/CMakeLists.txt') as cmake:
                for line in cmake:
                    proj = project_name(line)
                    if proj:
                        projects[proj] = root
                        break
    return projects


def setup_ignored(root, ros):

    projects = extract_cmake_names(root+'/src')
    ignore_file = 'CATKIN_IGNORE' if ros == 1 else 'COLCON_IGNORE'
    for name in projects:
        if name in ignore:
            run(f'touch {projects[name]}/{ignore_file}')


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

    # install skeleton if ros_management does not appear in bashrc (first run)
    skel = f'{base_path}/skel/{distro}'
    bashrc = os.environ['HOME'] + '/.bashrc'
    with open(bashrc) as f:
        if 'ros_management_tools' not in f.read():
            copytree(skel + '/', os.environ['HOME'], dirs_exist_ok = True)

    # wallpaper
    wp = [f for f in os.listdir(base_path + '/images/') if ros2 in f][0]
    if not os.path.exists(f'{Depend.folders[Source.GIT]}/{wp}'):
        sudo.run(f'cp {base_path}/images/{wp} {Depend.folders[Source.GIT]}')

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
    if len(Depend.packages_old) and not args.no_upgrade:
        sudo.run('apt upgrade -qy')
        sudo.run('apt autoremove --purge -qy')

    # deb-based
    updated = [dep.update() for dep in to_install[Source.DEB]]
    if Source.DEB in updated:
        sudo.run('apt install -qy --fix-broken --fix-missing')

    # pip3 or script-based
    for dep in to_install[Source.PIP] + to_install[Source.SCRIPT]:
        dep.update()

    # git-based
    need_chmod = args.chmod or (len(to_install[Source.GIT]) > 0)
    for dep in to_install[Source.GIT]:
        dep.update()

    # ros ws
    updated = [dep.update() for dep in to_install[Source.GIT_ROS] + to_install[Source.GIT_ROS2]]
    # recompile ros1ws
    if Source.GIT_ROS in updated or (args.force_compile and os.path.exists(Depend.folders[Source.GIT_ROS])):
        if args.force_compile or not os.path.exists(f'{Depend.folders[Source.GIT_ROS]}/.catkin_tools'):
            # purge catkin install
            for folder in ('build','install','devel','log'):
                if os.path.exists(f'{Depend.folders[Source.GIT_ROS]}/{folder}'):
                    rmtree(f'{Depend.folders[Source.GIT_ROS]}/{folder}')

            out = run(f'catkin config --init --extend /opt/ros/{ros1} --install -DCATKIN_ENABLE_TESTING=False --make-args -Wno-dev --cmake-args -DCMAKE_BUILD_TYPE=Release',
                cwd=Depend.folders[Source.GIT_ROS])

            for line in out:
                if 'failed:' in out:
                    print(line)
        setup_ignored(Depend.folders[Source.GIT_ROS], 1)
        run(['catkin build  --continue-on-failure', f'Compiling ROS 1 auxiliary workspace @ {Depend.folders[Source.GIT_ROS]}'],
            cwd=Depend.folders[Source.GIT_ROS], show=True)
        need_chmod = True

    # recompile ros2ws
    if Source.GIT_ROS2 in updated or (args.force_compile and os.path.exists(Depend.folders[Source.GIT_ROS2])):

        if args.force_compile:
            root = Depend.folders[Source.GIT_ROS2]
            run(f'rm -rf {root}/build {root}/install {root}/log')

        setup_ignored(Depend.folders[Source.GIT_ROS2], 2)
        out = run([f'bash -c -i "source /opt/ros/{ros2}/setup.bash && {GZ}_VERSION={gz} colcon build --symlink-install --continue-on-error"',
             f'Compiling ROS 2 auxiliary workspace @ {Depend.folders[Source.GIT_ROS2]}'],
            cwd=Depend.folders[Source.GIT_ROS2], show=True)

        need_chmod = True

    if need_chmod:
        sudo.run([f'chmod a+rX {Depend.folders[Source.GIT]} -R', 'Setting permissions'])

    # check chmod for these ones
    if os.path.exists('/opt/coppeliaSim'):
        sudo.run('chmod a+rwX -R /opt/coppeliaSim',show=False)

    # poweroff only if no one else is connected
    if poweroff and all(user == Display.user for user in run('users')[0].split()):
        Display.stop(False)
        sudo.run('poweroff')
    else:
        Display.stop()


if __name__ != '__main__':
    sys.exit(0)

if args.test:
    # to test things
    Display.stop()

if isinstance(args.u, list):
    # '-u' was given
    to_update = [mod for mod in modules if mod in args.u]

    if len(to_update) == 0:
        # update all existing ones
        to_update = [mod for mod in modules if modules[mod].is_default()]

    for mod in to_update:
        modules[mod].configure(Action.INSTALL)

    s = 's' * min(1, len(to_update)-1)
    print(f'Will update / install the following module{s}: {", ".join(to_update)}')

    perform_update(poweroff=poweroff)


if args.all:
    # install / update all modules
    perform_update(Action.INSTALL,poweroff=poweroff)

sys._excepthook = sys.excepthook


def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


sys.excepthook = exception_hook

Display.endl()


# GUI part

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout,QHBoxLayout,QGridLayout, QLabel, QPushButton, QCheckBox, QComboBox, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QFont, QIcon


def Font(size = 10):
    return QFont("Helvetica", size, QFont.Bold)


class UpdaterGUI(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowIcon(QIcon(get_file('images/ecn-rob.png')))
        self.setWindowTitle('Virtual Machine updater')

        # build GUI
        layout = QVBoxLayout(self)
        font = Font()

        # top bar = groups
        groups_layout = QHBoxLayout()
        label = QLabel('Groups', self)
        label.setFont(Font(12))
        groups_layout.addWidget(label)

        for group in groups:

            groups_layout.addSpacing(10)
            groups[group] = {'cb': QCheckBox(self), 'modules': groups[group]}
            groups[group]['cb'].setText(group)
            groups[group]['cb'].setFont(font)
            groups_layout.addWidget(groups[group]['cb'])
            groups[group]['cb'].clicked.connect(self.group_update)

        layout.addLayout(groups_layout)
        layout.addSpacing(10)

        mod_layout = QGridLayout()
        spacer = QSpacerItem(10, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)

        valid = sorted([m for m in modules.values() if 'description' in m.config],
                       key = lambda m: m.name)
        for i,module in enumerate(valid):
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
        for name,group in groups.items():

            for module in group['modules']:
                module_checked[module] = module_checked[module] or group['cb'].isChecked()

        for name,checked in module_checked.items():
            module = modules[name]
            if checked and module.status != Status.INSTALLED:
                module.menu.setCurrentIndex(Action.INSTALL)
            else:
                module.menu.setCurrentIndex(Action.KEEP)


app = QApplication(sys.argv)
gui = UpdaterGUI()

app.exec_()
Display.stop()
