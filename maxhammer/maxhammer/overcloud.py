import codecs
import logging
import os
import stat
from jinja2 import Template, Environment, FileSystemLoader
from maxhammer import fileutil


class Overcloud:
    """
    Represents actions to build a personalized overcloud config
    """

    def __init__(self, config_path):
        """
        :param config_path: Path to the overcloud config(s). A list of paths is acceptable.
        :return:
        """
        self.config_path = config_path


    def process_overcloud_config_files(self, clouddata, output_path, include_list=[], exclude_list=[]):
        """
        Generate a personalized overcloud config environment based upon a clouddata config
        :param clouddata: De-serialized YAML of clouddata
        :param output_path: Output path for customized overcloud config
        :return:
        """
        # For each directory under that path (recursively)
        for rootdir, subdirList, fileList in os.walk(self.config_path):

            ENV = Environment(loader=FileSystemLoader(rootdir))

            # Process filters
            if exclude_list:
                subdirList[:] = [d for d in subdirList if not fileutil.check_include(rootdir, d, exclude_list)]
                fileList[:] = [f for f in fileList if not fileutil.check_include(rootdir, f, exclude_list)]
            if include_list:
                subdirList[:] = [d for d in subdirList if fileutil.check_include(rootdir, d, include_list)]
                fileList[:] = [f for f in fileList if fileutil.check_include(rootdir, f, include_list)]

            # For each file found in that directory
            for fname in fileList:

                logging.getLogger().debug("Jinjafying overcloud config file {}".format(fname))
                template = ENV.get_template(fname)
                try:
                    outputcontent = template.render(cloud=clouddata)
                    reldir = os.path.relpath(rootdir, self.config_path)
                    outputdir = os.path.join(output_path, reldir)
                except Exception as error:
                    logging.getLogger().error("Applying clouddata template to file {} failed: {}".format(
                        fname, str(error)))
                    raise Exception("An error occurred processing overcloud config area {}".format(self.config_path))

                try:
                    os.makedirs(outputdir)
                except OSError:
                    if not os.path.isdir(outputdir):
                        raise Exception("Unable to create output cached overcloud directory {}".format(outputdir))

                srcfile = os.path.join(rootdir, fname)
                destfile = os.path.join(outputdir, fname)
                with codecs.open(destfile, 'w', 'utf-8') as destination:
                #with open(destfile, 'w') as destination:
                    # first make the destination user-writable just in case it isn't
                    os.chmod(destfile,os.stat(srcfile).st_mode | stat.S_IWUSR)
                    destination.write(outputcontent)
                    os.chmod(destfile,os.stat(srcfile).st_mode)
                    logging.getLogger().info("Cached overcloud config for {} in {}".format(fname, outputdir))

