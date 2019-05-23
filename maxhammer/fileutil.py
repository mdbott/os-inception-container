import os
import fnmatch
import ConfigParser
import shutil
from dirtools import Dir


class DirWithSymlinks(Dir):
    """
    Extends the dirtools Dir class to override the walk() method with one that will
    include symlinks as files (rather than ignore them)
    """

    def __init__(self, directory=".", exclude_file=".exclude",
                 excludes=['.git/', '.hg/', '.svn/']):
        super(DirWithSymlinks, self).__init__(directory, exclude_file, excludes)

    def walk(self):
        for root, dirs, files in os.walk(self.path, topdown=True):
            ndirs = []
            # First we exclude directories
            for d in list(dirs):
                if self.is_excluded(os.path.join(root, d)):
                    dirs.remove(d)
                elif not os.path.islink(os.path.join(root, d)):
                    ndirs.append(d)

            nfiles = []
            for fpath in (os.path.join(root, f) for f in files):
                if not self.is_excluded(fpath):
                    nfiles.append(os.path.relpath(fpath, root))

            yield root, ndirs, nfiles


def _read_filter_config(config_file,filter_type):
    assert filter_type in ["distribution","processing"]

    config = ConfigParser.ConfigParser()
    config.read(config_file)
    try:
        raw_filters = config.get(filter_type,'filterlist')
        return list(filter(None, (x.strip() for x in raw_filters.splitlines())))
    except ConfigParser.NoSectionError:
        return []


def _get_exclude_files(fromdir,ignorefile):
    exclude_files = []
    d = DirWithSymlinks(fromdir)
    for dir in d.subdirs() + ['./']:
        project_file = os.path.join(fromdir,dir,ignorefile)
        p2file = os.path.join(dir,ignorefile)

        if os.path.isfile(project_file):
            exclude_files.append(p2file)
    return exclude_files


def _build_exclude_list(fromdir, filter_type, exclude_list):
    assert filter_type in ["distribution","processing"]
    excludes = []
    for file in exclude_list:
        relpath = os.path.dirname(file)
        fullpath = os.path.join(fromdir,file)
        st = os.stat(fullpath)
        if st.st_size == 0:
            excludes.append(os.path.dirname(file))
            continue

        excl_list = [os.path.join(relpath,x) for x in _read_filter_config(fullpath,filter_type)]
        excludes.extend(excl_list)

    return excludes


def get_files_with_exclusion_status(fromdir,job="processing",ignorefile=".mhignore"):
    """
    Returns a tuple of files contained in the supplied directory and a boolean indicating whether
    the supplied exclude filters mean it should be excluded.
    :param fromdir:
    :param job:
    :param ignorefile:
    :return:
    """
    if ignorefile:
        exclude_files = _get_exclude_files(fromdir,ignorefile)
        exclude_list = _build_exclude_list(fromdir,job,exclude_files)
    else:
        exclude_list = []

    d = DirWithSymlinks(fromdir, excludes=[])
    d_exclude = DirWithSymlinks(fromdir, excludes=exclude_list)
    exclude_files = d_exclude.files()
    stuff = [(x,x not in exclude_files) for x in d.files()]
    return stuff


def clone_with_filter(fromdir,todir,job="processing",ignorefile=".mhignore"):

    exclude_files = _get_exclude_files(fromdir,ignorefile)
    exclude_list = _build_exclude_list(fromdir,job,exclude_files)
    d = DirWithSymlinks(fromdir, excludes=exclude_list)

    for dir in d.subdirs():
        from_dir = os.path.join(fromdir,dir)
        dir_stat = os.stat(from_dir)
        to_dir = os.path.join(todir,dir)
        os.mkdir(to_dir,dir_stat.st_mode)

    for file in d.files():
        from_file = os.path.join(fromdir,file)
        to_file = os.path.join(todir,file)
        shutil.copy2(from_file,to_file)


def check_include(rootdir, path, include_list):
    """
    Checks whether a file is present within the list of supplied paths. The function will also
    check if any of the supplied paths are a directory which contains the file being searched for,
    and succeed if that is the case.
    :param path: File to check
    :param include_list: List of paths (directories or files) to check
    :return: True if the file is present in the list or a child of a path in the list, false otherwise
    """
    path = os.path.normpath(os.path.realpath(os.path.join(rootdir,path)))
    for i in include_list:
        check_path = os.path.normpath(os.path.realpath(i))
        pi = check_path + '*'
        if fnmatch.fnmatch(path,pi):
            return True
    return False


