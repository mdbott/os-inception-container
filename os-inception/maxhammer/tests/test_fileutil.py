import unittest
import os
from maxhammer import fileutil


class TestFileUtil(unittest.TestCase):

    def test_contains_file_fullpath(self):
        rootdir = os.path.abspath('fileutil')
        dir1dir = os.path.abspath('fileutil/dir1')
        dir11dir = os.path.abspath('fileutil/dir1/dir1-1')
        dir2dir = os.path.abspath('fileutil/dir2')

        # check that an empty include list results in no match
        self.assertFalse(fileutil.check_include(rootdir, 'file0-1', []))

        # checks if rootdir contains rootdir/file-1-1 (should succeed)
        self.assertTrue(fileutil.check_include(rootdir, 'file-1-1', [rootdir]))

        # checks if rootdir contains rootdir/file-1-1 (should succeed)
        self.assertTrue(fileutil.check_include(rootdir, 'dir1/file-1-1', [dir1dir]))

        # checks if rootdir/dir1 contains rootdir/file0-1 (should fail)
        self.assertFalse(fileutil.check_include(rootdir, 'file0-1', [dir1dir]))

        # checks if rootdir/dir2 contains rootdir/dir1/file1-1 (should fail)
        self.assertFalse(fileutil.check_include(rootdir, 'dir1/file1-1', [dir2dir]))

        # checks if rootdir contains rootdir/dir1
        self.assertTrue(fileutil.check_include(rootdir, 'dir1', [rootdir]))

        # checks if rootdir contains rootdir/dir2
        self.assertTrue(fileutil.check_include(rootdir, 'dir2', [rootdir]))

        # checks if rootdir/dir1 contains rootdir/dir1/dir1-1
        self.assertTrue(fileutil.check_include(rootdir, 'dir1/dir1-1', [dir1dir]))

        # checks if rootdir/dir2 contains rootdir/dir1/dir1-1
        self.assertFalse(fileutil.check_include(rootdir, 'dir1/dir1-1', [dir2dir]))

        # checks if rootdir contains rootdir/dir2/../dir1
        self.assertTrue(fileutil.check_include(rootdir, 'dir2/../dir1', [rootdir]))

        # checks if rootdir contains rootdir/../
        self.assertFalse(fileutil.check_include(rootdir, '../', [rootdir]))
        self.assertFalse(fileutil.check_include(rootdir, '..', [rootdir]))

        # checks if rootdir/dir1/../dir2/ contains rootdir/dir2/file2-1
        self.assertTrue(fileutil.check_include(rootdir, 'dir2/file2-1', [dir1dir + '/../dir2/']))

        # check that directories are handled properly
        self.assertTrue(fileutil.check_include(rootdir, 'dir1/.git', [rootdir + '/dir1/.git']))

        # check that trailing slashes aren't a problem
        self.assertTrue(fileutil.check_include(rootdir, 'dir1/.git', [rootdir + '/dir1/.git/']))
        self.assertTrue(fileutil.check_include(rootdir, 'dir1/.git/', [rootdir + '/dir1/.git/']))

    def test_contains_file_re_path(self):

        rootdir = os.path.abspath('fileutil')
        dir1dir = os.path.abspath('fileutil/dir1')
        dir11dir = os.path.abspath('fileutil/dir1/dir1-1')
        dir2dir = os.path.abspath('fileutil/dir2')

        # standard tests of correct functionality
        self.assertTrue(fileutil.check_include(rootdir, 'dir1', [rootdir + '/*']))
        self.assertTrue(fileutil.check_include(rootdir, 'dir2/file2-1', [rootdir + '/dir2/f*le*1']))
        self.assertTrue(fileutil.check_include(rootdir, 'dir2/file2-1', [rootdir + '*/dir2']))
        self.assertTrue(fileutil.check_include(rootdir, 'dir1/dir1-1/abc', [rootdir + '*/dir2/../*/dir1-1']))


        # check that dots don't get treated as a wildcard
        self.assertFalse(fileutil.check_include(rootdir, 'dir1/agit', [rootdir + '/dir1/.git']))


if __name__ == '__main__':
    unittest.main()