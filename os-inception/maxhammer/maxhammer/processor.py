import codecs
import os
import stat
import logging
import shutil
from jinja2 import Template, Environment, FileSystemLoader
from maxhammer import fileutil

GENERIC = 1
ANSIBLE = 2


class Processor:
    """
    Pre-processes files via Jinja2 prior to distribution
    """

    def __init__(self, config_path=None, logger=None):
        """
        :param config_path: Path to the overcloud config(s). A list of paths is acceptable.
        :return:
        """
        self.config_path = config_path
        self.logger = logger or logging.getLogger(__name__)


    def _get_ansible_environment(self):
        """
        Returns a Jinja processing environment suitable for Ansible-based configs
        :return:
        """
        env = Environment(block_start_string='[%',block_end_string='%]',
            variable_start_string='[{',variable_end_string='}]',
            loader=FileSystemLoader(self.config_path))
        return env


    def _get_generic_engine(self):
        """
        Returns a default Jinja processing environment suitable for most configs.
        :return:
        """
        env = Environment(loader=FileSystemLoader(self.config_path))
        return env


    def run(self, clouddata, output_path, process_method=GENERIC):
        """
        Generate a personalized overcloud config environment based upon a clouddata config
        :param clouddata: De-serialized YAML of clouddata
        :param output_path: Output path for customized overcloud config
        :param process_method Indicates pre-processing method to apply
        :return:
        """

        if process_method == GENERIC:
            env = self._get_generic_engine()
        elif process_method == ANSIBLE:
            env = self._get_ansible_environment()
        else:
            raise Exception("Invalid process method provided.")

        files_to_process = fileutil.get_files_with_exclusion_status(self.config_path)
        for file,should_be_excluded in files_to_process:
            srcfile = os.path.join(self.config_path, file)
            destfile = os.path.join(output_path, file)

            # first try and create the output dir
            try:
                outputdir = os.path.join(output_path,os.path.dirname(file))
                self.logger.debug("Creating dir: {}".format(outputdir))
                os.makedirs(outputdir)
            except OSError:
                if not os.path.isdir(outputdir):
                    raise Exception("Unable to create output cached directory {}".format(outputdir))

            # if the file doesn't need processing, just copy it
            if should_be_excluded:
                shutil.copyfile(srcfile,destfile)
                continue

            self.logger.debug("Jinjafying config file {}".format(file))
            template = env.get_template(file)
            try:
                outputcontent = template.render(cloud=clouddata)
            except Exception as error:
                self.logger.error("Applying clouddata template to file {} failed: {}".format(
                    file, str(error)))
                raise Exception("An error occurred processing config area {}".format(self.config_path))

            with codecs.open(destfile, 'w', 'utf-8') as destination:
                # first make the destination user-writable just in case it isn't
                os.chmod(destfile,os.stat(srcfile).st_mode | stat.S_IWUSR)
                destination.write(outputcontent)
                os.chmod(destfile,os.stat(srcfile).st_mode)
                self.logger.info("Cached config for {} in {}".format(file, outputdir))

