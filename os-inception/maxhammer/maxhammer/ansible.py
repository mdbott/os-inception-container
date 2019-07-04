import codecs
import logging
import os
from maxhammer import fileutil
from jinja2 import Template, Environment, FileSystemLoader


class Ansible:
    """
    Class representing the build of an ansible environment
    """

    def __init__(self, config_path):
        """
        :param config_path: Path to the core ansible config
        :return:
        """
        self.config_path = config_path


    def process_ansible_config_files(self, clouddata, output_path, include_list=[], exclude_list=[]):
        """
        Generate a personalized ansible config environment based upon a clouddata config
        :param clouddata: De-serialized YAML of clouddata
        :param output_path: Output path for customized ansible config
        :return:
        """
        for rootdir, subdirList, fileList in os.walk(self.config_path):
            env = Environment(block_start_string='[%',block_end_string='%]',
                              variable_start_string='[{',variable_end_string='}]',
                            loader=FileSystemLoader(rootdir))

            if exclude_list:
                subdirList[:] = [d for d in subdirList if not fileutil.check_include(rootdir, d, exclude_list)]
                fileList[:] = [f for f in fileList if not fileutil.check_include(rootdir, f, exclude_list)]
            if include_list:
                subdirList[:] = [d for d in subdirList if fileutil.check_include(rootdir, d, include_list)]
                fileList[:] = [f for f in fileList if fileutil.check_include(rootdir, f, include_list)]

            for fname in fileList:

                logging.getLogger().debug("Jinjafying ansible config file {}".format(fname))
                template = env.get_template(fname)

                try:
                    outputcontent = template.render(cloud=clouddata)
                    reldir = os.path.relpath(rootdir, self.config_path)
                    outputdir = os.path.join(output_path, reldir)
                except Exception as error:
                    logging.getLogger().error("Applying clouddata template to file {} failed: {}".format(
                        fname, str(error)))
                    raise Exception("An error occurred processing ansible config area {}".format(
                            os.path.join(rootdir, fname)))

                try:
                    os.makedirs(outputdir)
                except OSError:
                    if not os.path.isdir(outputdir):
                        raise Exception("Unable to create output cached ansible directory {}".format(outputdir))

                srcfile = os.path.join(rootdir, fname)
                destfile = os.path.join(outputdir, fname)
                with codecs.open(destfile, 'w', 'utf-8') as destination:
                #with open(destfile, 'w') as destination:
                    destination.write(outputcontent)
                    os.chmod(destfile,os.stat(srcfile).st_mode)
                    logging.getLogger().info("Cached ansible config for {}".format(os.path.join(outputdir,fname)))
