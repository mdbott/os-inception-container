import paramiko
import os
import logging
from maxhammer import fileutil
from stat import S_ISDIR, S_IWUSR

class Server(object):
    """
    Wraps paramiko for super-simple SFTP uploading and download.
    """

    def __init__(self,  host, username='root', password=None, key_file=None, port=22):

        self.transport = paramiko.Transport((host, port))
        self.transport.start_client()
        # keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        key = self.transport.get_remote_server_key()
        if key_file is not None:
            # if isinstance(key, str):
            #     key_object = open(key, 'r')
            # else:
            #     key_object = key
            # key_head = key_object.readline()
            # key_file.seek(0)
            # if 'DSA' in key_head:
            #     keytype = paramiko.DSSKey
            # elif 'RSA' in key_head:
            #     keytype = paramiko.RSAKey
            # else:
            #     raise Exception("Can't identify key type")
            keytype = paramiko.RSAKey
            pkey = keytype.from_private_key(key_file)
            self.transport.auth_publickey(username, pkey)
        else:
            if password is not None:
                self.transport.auth_password(username, password, fallback=False)
            else:
                raise Exception('Must supply either key_file or password')
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)


    def upload_filtered(self, localpath, remotepath, include_list=[], exclude_list=[]):

        # Create the base remote path first
        try:
            self.sftp.mkdir(remotepath)
        except:
            pass

        # Switch to the directory we wnat to copy across
        os.chdir(localpath)
        for root, dirs, files in os.walk('.'):
        #for root, dirs, files in os.walk(localpath):
            if exclude_list:
                #dirs[:] = [d for d in dirs if not os.path.join(root, d) in exclude_list]
                dirs[:] = [d for d in dirs if not fileutil.check_include(root, d, exclude_list)]
                files[:] = [f for f in files if not fileutil.check_include(root, f, exclude_list)]

            if include_list:
                dirs[:] = [d for d in dirs if fileutil.check_include(root, d, include_list)]
                files[:] = [f for f in files if fileutil.check_include(root, f, include_list)]

            try:
                remote_create_path = os.path.join(remotepath, root)
                logging.getLogger().debug("Creating remote dir {}".format(remote_create_path))
                self.sftp.mkdir(remote_create_path)
            except:
                pass

            for file in files:
                source_file_path = os.path.join(root, file)
                remote_file_path = os.path.join(remote_create_path, file)
                logged_source_file_path = os.path.join(localpath, source_file_path)
                logging.getLogger().debug("Uploading file FROM: {} TO: {}".format(source_file_path, remote_file_path))
                self.upload(source_file_path, remote_file_path)


    def get_perms(self, localfile):
        statdata = os.stat(localfile)


    def upload(self, localfile, remotefile, preserve_permission=True):
        # If the remote file already exists, make it user-writable
        try:
            self.sftp.stat(remotefile)
            self.sftp.chmod(remotefile, os.stat(localfile).st_mode | S_IWUSR)
        except IOError, e:
            pass

        # then attempt to upload
        try:
            self.sftp.put(localfile, remotefile)
            if preserve_permission:
                self.sftp.chmod(remotefile, os.stat(localfile).st_mode)
        except Exception as error:
            raise Exception("Error uploading {} to remote location {}: {}".format(localfile,remotefile,str(error)))


    def upload_all(self, localpath, remotepath):
        # Recursively upload a full directory
        os.chdir(os.path.split(localpath)[0])
        parent = os.path.split(localpath)[1]
        for walker in os.walk(parent):
            try:
                self.sftp.mkdir(os.path.join(remotepath, walker[0]))
            except:
                pass
            for file in walker[2]:
                self.upload(os.path.join(walker[0], file), os.path.join(remotepath, walker[0], file))

    def download(self, remote, local):
        self.sftp.get(remote, local)

    def sftp_walk(self, remotepath):
        # Kind of a stripped down version of os.walk, implemented for sftp.
        path = remotepath
        files = []
        folders = []
        for f in self.sftp.listdir_attr(remotepath):
            if S_ISDIR(f.st_mode):
                folders.append(f.filename)
        print (path, folders, files)
        yield path, folders, files
        for folder in folders:
            new_path = os.path.join(remotepath, folder)
            for x in self.sftp_walk(new_path):
                yield x

    def download_all(self, remotepath, localpath):
        self.sftp.chdir(os.path.split(remotepath)[0])
        parent = os.path.split(remotepath)[1]
        try:
            os.mkdir(localpath)
        except:
            pass
        for walker in self.sftp_walk(parent):
            try:
                os.mkdir(os.path.join(localpath,walker[0]))
            except:
                pass
            for file in walker[2]:
                self.download(os.path.join(walker[0], file), os.path.join(localpath, walker[0], file))

    def close(self):
        """
        Close the connection if it's active
        """
        if self.transport.is_active():
            self.sftp.close()
            self.transport.close()

    # with statement support
    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()


