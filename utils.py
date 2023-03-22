import glob,os,re
from pathlib import Path
from config import *

class BulkInferenceHelper:
    def get_framework(self, model_path: str) -> str:
        caffe2_onnx = os.path.join("caffe2", "onnx")
        if model_path.find(caffe2_onnx) != -1:
            return "caffe2"

        if model_path.find("onnx") != -1:
            return ["onnx", "pytorch"]

        if model_path.find("mxnet") != -1:
            return ["mxnet"]

        if model_path.find("caffe2") != -1:
            return ["caffe2"]

        if model_path.find("caffe") != -1:
            return ["caffe"]

        if model_path.find("tf2") != -1:
            return ["tf2"]

        if model_path.find("tf") != -1:
            return ["tf"]

        if model_path.find("paddle") != -1:
            return ["paddle"]

        return None

    def get_framework2(self, model_path: str) -> str:
        caffe2_onnx = os.path.join("caffe2", "onnx")
        if model_path.find(caffe2_onnx) != -1:
            return ["caffe2", "pytorch"]

        caffe_onnx = os.path.join("caffe2", "onnx")
        if model_path.find(caffe_onnx) != -1:
            return ["caffe", "pytorch"]

        return None

    def exists(self, directory: str, file_name: str) -> str:
        for file_path in Path(directory).glob(os.path.join("**", file_name)):
            return file_path
        return None

    def find_yaml_file(self, model_path, configs_path: str) -> str:
        yml_config_name_without_ext = os.path.splitext(os.path.basename(model_path))[0]

        # find folder with given name
        yml_config_path = self.exists(configs_path, yml_config_name_without_ext)
        if yml_config_path:
            yml_config_path = self.exists(yml_config_path, "accuracy-check.yml")
            if yml_config_path:
                return yml_config_path

        yml_config_path = self.exists(configs_path, yml_config_name_without_ext + ".yml")
        if yml_config_path:
            return yml_config_path

        frameworks = self.get_framework(model_path)
        if frameworks:
            for framework in frameworks:
                yml_config_path = self.exists(configs_path, "{}-{}.yml".format(yml_config_name_without_ext, framework))
                if yml_config_path:
                    return yml_config_path

        frameworks = self.get_framework2(model_path)
        if frameworks:
            for framework in frameworks:
                yml_config_path = self.exists(configs_path, "{}-{}.yml".format(yml_config_name_without_ext, framework))
                if yml_config_path:
                    return yml_config_path

        return None


def find_yaml_file(model_path) -> str:
    bi = BulkInferenceHelper()
    for yml_path in accuracy_checker_configs:
        yml_file = bi.find_yaml_file(model_path, yml_path)
        if yml_file:
            return yml_file
    #raise Exception(f"cannot find accuracy checker config for {model_path} in {accuracy_checker_configs}")
    return None


'''
def get_models_xml(model_base, name_filter):
    models = []
    # user can specify path to override model_base
    # or a pattern of path to filter subset of models in model_base
    if os.path.isdir(name_filter):
        model_base = name_filter
    for root, dirs, files in os.walk(model_base):
        for file in files:
            if os.path.splitext(file)[1] == ".xml":
                fullpath = os.path.join(root, file)
                if (name_filter in fullpath):
                    models.append(fullpath)
                    found_xml = models[-1][len(model_base):]
                    print(f"{len(models)}:  {found_xml}")
    return models
'''

# name_filters: filters separated with ",", each filter can be
#
#    path        all .xml files recusivedly found under path
#    path:kw     all .xml files whose full path contains kw substring
#    :kw         model_base is the path
#    kw          same as :kw when kw is not exist as path
#
def get_models_xml(model_base, name_filters = ""):
    models = []
    for name_filter in name_filters.split(","):
        # user can specify path to override model_base
        # or a pattern of path to filter subset of models in model_base
        #
        if ":" in name_filter:
            path, kw = name_filter.split(":")
            if len(path)==0:
                path_list = model_base
            else:
                path_list = [path]
        else:
            if os.path.isdir(name_filter):
                path_list = [name_filter]
                kw = ''
            elif os.path.isfile(name_filter):
                models.append(name_filter)
                print(f"{len(models)}:  {name_filter}")
                continue
            else:
                path_list = model_base
                kw = name_filter

        for path in path_list:
            print(f"searching models (keyword:{kw}) in {path} ...")
            for root, dirs, files in os.walk(path):
                for f in files:
                    if os.path.splitext(f)[1] == ".xml":
                        fullpath = os.path.join(root, f)
                        if (kw in fullpath):
                            if not "intermediate_model.xml" in fullpath:
                                models.append(fullpath)
                                found_xml = models[-1][len(path):]
                            #print(f"{len(models)}:  {found_xml}")
    return models

def gen_device_config(device_config_path, bf16):
    ENFORCE_BF16 = "YES" if bf16 else "NO"
    with open(device_config_path, "w") as devcfg_file:
        devcfg_file.write(f'CPU:\n')
        devcfg_file.write(f'    ENFORCE_BF16: "{ENFORCE_BF16}"\n')
        devcfg_file.write(f'    NUM_STREAMS: 1\n')

# path prefix
def get_common_prefix(lines):
    def find_common_prefix(a, cur_prefix):
        cur_prefix = cur_prefix[:len(a)]
        last_sep = 0
        for i in range(0, len(cur_prefix)):
            if cur_prefix[i] != a[i]:
                return cur_prefix[:last_sep + 1]
            if cur_prefix[i] == os.path.sep:
                last_sep = i
        return cur_prefix

    comm_prefix = lines[0]
    for i in range(1, len(lines)):
        comm_prefix = find_common_prefix(lines[i], comm_prefix)
    return comm_prefix

def get_models_xmlyml_from_list(model_list, name_filter = ""):
    models = []
    with open(model_list, "r") as flist:
        for line in flist.readlines():
            xml,yml = line.split()
            for nf in name_filter.split(","):
                if nf in xml:
                    models.append((xml, yml))
                    break
    return models

if __name__ == "__main__":
    import argparse
    import sys
    import shutil

    def valid_path(s):
        if os.path.isdir(s):
            return s
        else:
            raise Exception("Path is not exist")

    parser = argparse.ArgumentParser(description=f"Test utils")
    parser.add_argument("--ext", type=str, default=None)
    parser.add_argument("--reg", action="store_true")
    parser.add_argument("--collect", type=valid_path)
    parser.add_argument("--kw", type=str, default="")
    parser.add_argument("--to", type=valid_path)
    args = parser.parse_args()

    if args.reg:
        pat = re.compile("(\d*(?:%|Db))")
        print(pat.match("8%"))
        print(pat.match("8Db"))
        m = re.compile(".*accuracy_check.*-c\s+([^ ]*)\s").match("+ accuracy_check --target_framework dlsdk -td CPU --device_config acc_s10_22.1/device_config.yml --definitions /home/dev/common/accuracy-checker/configs/omz_validation//dataset_definitions.yml --source /home/dev/common/odt_nfs_share/omz-validation-datasets --annotations /home/dev/common/annotations --models /home/dev/common/inn_nfs_share/cv_bench_cache/sk_13sept_75models_22.1_int8/se-resnext-50/caffe/caffe/FP16/INT8/1/dldt/optimized/se-resnext-50.xml -c /home/dev/common/accuracy-checker/configs/omz_validation/public_omz_package/se-resnext-50-caffe.yml --shuffle False -ss 10")
        print(m.group(1))

    if args.ext:
        results, base = extract_accuracy(args.ext)
        for i, r in enumerate(results):
            print(f"[{i:3}/{len(results)}] : {results[r]}")
        print(f"base = {base}")
        sys.exit(0)
    
    if args.collect:
        num_models = 0
        model_base = args.collect.rstrip("/")

        with open("./list.txt","w") as flist:
            for dir in os.listdir(model_base):
                print(dir, os.path.isdir(dir))

                path = os.path.join(model_base, dir)
                kw = args.kw
                #print(f"searching models (keyword:{kw}) in {path} ...")
                for root, dirs, files in os.walk(path):
                    for f in files:
                        if os.path.splitext(f)[1] == ".xml":
                            fullpath = os.path.join(root, f)
                            if (kw in fullpath):
                                if not "intermediate_model.xml" in fullpath:
                                    #models.append(fullpath)
                                    yml_src = find_yaml_file(fullpath)
                                    if not yml_src:
                                        print(fullpath, "No yml found")
                                        continue
                                    yml_copy = os.path.join(args.to, os.path.basename(yml_src))
                                    shutil.copyfile(yml_src, yml_copy)
                                    flist.write(f"{fullpath} {yml_copy}\n")
                                    flist.flush()
                                    print(fullpath, yml_copy)

            #num_models += len(models)
            #models = utils.get_models_xml(utils.model_base, model_name)
            #for i, xml in enumerate(models):
            #    accyml = utils.find_yaml_file(xml)
            #    if accyml is None:
            #        print(f"# yml is not found for {xml}")
            #    else:
            #        print("doTest", k, xml, accyml)
            #    k += 1
