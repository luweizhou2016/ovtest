import argparse
import os, sys, re
import utils
from colorama import Fore

from openvino.runtime import Core, Model, Tensor, PartialShape, Type, Shape, op, serialize

_comment_='''

python3 -m pip install -e ~/openvino/thirdparty/open_model_zoo/tools/accuracy_checker/

python3 setup.py install_as_extension --accuracy-checker-dir=

python3 -m pip install -e ~/openvino/tools/mo/
python3 -m pip install -e ~/openvino/tools/pot


thirdparty/open_model_zoo/tools/accuracy_checker/openvino/tools/accuracy_checker/metrics/image_quality_assessment.py

@@ -466,7 +466,7 @@ class LPIPS(BaseRegressionMetric):
             if isinstance(weights, tuple):
                 weights = weights[1] if torch.__version__ <= '1.6.0' else weights[0]
             preloaded_weights = torch.utils.model_zoo.load_url(
-                weights, model_dir=model_dir, progress=False, map_location='cpu'
+                weights, model_dir="lpips_models", progress=False, map_location='cpu'
             )
         model = model_classes[net](pretrained=False)
         model.load_state_dict(preloaded_weights)


mkdir lpips_models && cd lpips_models
wget https://download.pytorch.org/models/alexnet-owt-7be5be79.pth
wget https://download.pytorch.org/models/alexnet-owt-4df8aa71.pth
wget https://download.pytorch.org/models/squeezenet1_1-b8a52dc0.pth
wget https://download.pytorch.org/models/vgg16-397923af.pth

'''

class oneAccuracyTest:
    IE_version = re.compile("IE version:(.*)")
    CPU_version = re.compile("    CPU - openvino_intel_cpu_plugin: (.*)")
    number = "[-+]?[0-9]*\.?[0-9]+"
    Metric = re.compile(f"([A-Za-z0-9_\-@:\.]+): ({number})(?:%|Db)?")
    EndMark = f"\s*(\d*) objects processed in ({number}) seconds"
    def __init__(self, model, yml):
        self.model = model
        self.yml = yml
        self.metric = {}
    def parse(self, line):
        m = self.__class__.IE_version.match(line)
        if m:
            self.IE_version = m.group(1)
            return
        m = self.__class__.CPU_version.match(line)
        if m:
            self.CPU_version = m.group(1)
            return
        m = self.__class__.Metric.match(line)
        if m:
            self.metric[m.group(1)] = m.group(2)

    def repr_metric(self):
        return ",".join([f"{m}={v}" for m,v in self.metric.items()])
    def __repr__(self):
        ret = self.model
        if len(self.metric) == 0:
            ret += " [ERROR_no_metric] "
        else:
            ret += " "
            ret += self.repr_metric()
        return ret
    
    def better_direction(self, metric_name):
        if metric_name.startswith("accuracy"):
            return 1
        if metric_name.startswith("psnr"):
            return 1
        if "precision" in metric_name:
            return 1
        if metric_name.startswith("lpips@mean"):
            return -1
        if metric_name.startswith("wer"):
            return -1
        if metric_name == "map":
            return 1
        if metric_name == "focused_text_hmean":
            return 1
        if metric_name == "Perplexity":
            return -1
        if metric_name.startswith("mean_iou"):
            return 1
        if metric_name == "mpjpe_multiperson":
            return -1
        if metric_name.startswith("pckh@"):
            return 1
        if metric_name.startswith("AP@"):
            return 1
        if metric_name == "F1":
            return 1
        if metric_name == "EM":
            return 1
        if metric_name.startswith("spearman@"):
            return 1
        if metric_name.startswith("pearson@"):
            return 1
        return 0

def extract_accuracy(log_file_path):
    acc_model = re.compile(".*accuracy_check.*(?:-m|--models)\s+([^ ]*)\s")
    acc_yml = re.compile(".*accuracy_check.*(?:-c|--config)\s+([^ ]*)\s")
    def get_oneTest(line):
        m0 = acc_model.match(line)
        if not m0:
            return None
        m1 = acc_yml.match(line)
        if not m1:
            return None
        return oneAccuracyTest(m0.group(1), m1.group(1))

    with open(log_file_path, "r") as log_file:
        results = []
        cur_test = None
        for line in log_file.readlines():
            new_test = get_oneTest(line)
            if new_test:
                if cur_test:
                    results.append(cur_test)
                cur_test = new_test
            elif cur_test:
                cur_test.parse(line)
        if cur_test:
            results.append(cur_test)

    # extract common base from the model path and remove it if possible
    comm_prefix = utils.get_common_prefix([r.model for r in results])
    
    # convert results into a dict with model subpath as key
    ret = {}
    for r in results:
        r.model = r.model[len(comm_prefix):]
        ret[r.model] = r

    return ret, comm_prefix

def compare_acc_results(ref_log_path, tgt_log_path, args, rel_warn_thr = 0.2):
    ref, base0 = extract_accuracy(ref_log_path)
    tgt, base1 = extract_accuracy(tgt_log_path)
    N = len(tgt)
    E = 0
    for i, (model, r) in enumerate(tgt.items()):
        if not model in ref:
            print(f"[{i}/{N}] {r} no match")
            continue
        
        # compare the metric
        def compare_metrics(m0, m1):
            max_diff_abs = 0
            max_diff_rel = 0
            def update_diff(v0, v1):
                nonlocal max_diff_abs, max_diff_rel
                diff_abs = abs(v1 - v0)
                diff_rel = diff_abs / v0 if v0 != 0 else float ('nan')
                max_diff_abs = max(max_diff_abs, diff_abs)
                max_diff_rel = max(max_diff_rel, diff_rel)
            description = ""
            all_better = True
            for k in m1:
                if k in m0:
                    v0 = float(m0[k])
                    v1 = float(m1[k])
                    direction = r.better_direction(k)
                    if (v0 != v1):
                        if direction > 0 and v1 > v0:
                            # better, Np
                            description += f' {Fore.GREEN} {k}: {v0}->{v1} {Fore.RESET}'
                            continue
                        if direction < 0 and v1 < v0:
                            description += f' {Fore.GREEN} {k}: {v0}->{v1} {Fore.RESET}'
                            # better, Np
                            continue
                        update_diff(v0, v1)
                        color = Fore.RED
                        if v0 !=0:
                            if abs(v1-v0)/v0 < rel_warn_thr:
                                color = Fore.YELLOW
                        description += f' {color} {k}: {v0}->{v1} {Fore.RESET}'
                        all_better = False
            return all_better, max_diff_abs, max_diff_rel, description

        all_better, max_diff_abs, max_diff_rel, description = compare_metrics(ref[model].metric, r.metric)
        #if not all_better and max_diff_rel > 0.05:
        E+=1
        if all_better:
            key_msg = f"{Fore.GREEN} -- {Fore.RESET}"
            if args.verbose > 0:
                print(f"({E}) {key_msg} [{i}/{N}] {model}  {description} ")
        else:
            key_msg = f"{Fore.RED} {max_diff_rel*100:.1f}% {Fore.RESET}"
            print(f"({E}) {key_msg} [{i}/{N}] {model}  {description} ")

if __name__ == "__main__":

    def infer_prec(prec):
        if prec == "bf16" or prec == "f16" or prec == "f32":
            return prec
        else:
            raise Exception(f"unsupported inference precision: {prec}")

    parser = argparse.ArgumentParser(description=f"Test accuracy")
    parser.add_argument("-f", "--name_filter", type=str, help="target model name filter", default="")
    parser.add_argument("-s", "--subset", type=int, help="subset size", default=0)
    parser.add_argument("--prec", type=infer_prec, default="f32")
    parser.add_argument("--eg", action="store_true")
    parser.add_argument("-l", "--model_list", type=str, default="int8_models/ww06_list.txt")
    parser.add_argument("-d", "--data-source", type=str, default=utils.data_source)
    parser.add_argument("--cmp", nargs="+")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("--tag", type=str, default=None)

    args = parser.parse_args()

    if (args.cmp):
        assert(len(args.cmp) <= 2)
        if len(args.cmp) == 1:
            res_dict, base0 = extract_accuracy(args.cmp[0])
            
            for i, (path, r) in enumerate(res_dict.items()):
                rtxt = repr(r)
                prefix = ""
                suffix = ""
                if "[ERROR_no_metric]" in rtxt:
                    prefix = Fore.RED
                    suffix = Fore.RESET
                
                print(f"{prefix}({i}): {r}{suffix}")
            print(f"base = {base0}")
        else:
            compare_acc_results(args.cmp[0], args.cmp[1], args)
        sys.exit(0)

    device_config_path = f"device_config_{args.prec}.yml"

    if args.subset > 0:
        ACCCFG = f" --shuffle False -ss {args.subset}"
    else:
        ACCCFG = ""

    print(f"searching for xml models in {args.model_list}...")
    models = utils.get_models_xmlyml_from_list(args.model_list, args.name_filter)

    if args.verbose > 0:
        os.environ["OV_CPU_DEBUG_LOG"] = "-"

    # ensure annotations folder exist
    os.system(f"mkdir -p {utils.annotations}")
    for i, (xml, accyml) in enumerate(models):
        # accyml = utils.find_yaml_file(xml)

        prefix = ""
        if (accyml is None):
            print(f"# cannot find yml for model: {xml} ")
            accyml="????"
            prefix="# "

        mpath = xml
        if args.tag:
            tags = f"-tt {args.tag}"
        else:
            tags = ""

        # try dataset definitions one by one until accuracy_check success
        for definitions_file in utils.definitions_file:
            acc_cmd = f"{prefix}accuracy_check --target_framework dlsdk -td CPU {tags} --use_new_api 1 --device_config {device_config_path} --definitions {definitions_file} --source {args.data_source} --annotations {utils.annotations} --model_attributes {utils.model_attributes} --models {mpath} -c {accyml} {ACCCFG}"
            print(f"======================={i}/{len(models)}")
            print(f"$ {acc_cmd}", flush=True)
            retv = os.system(acc_cmd)
            if retv == 0:
                break
            else:
                # exit on Ctrl+C
                if (retv % 256) == 130:
                    os.exit(retv)

        # serialize exec graph
        if args.eg:
            if not 'core' in globals():
                core = Core()
            exec_graph_fname = f"execgraph_{os.path.splitext(os.path.basename(mpath))[0]}.xml"

            org_model = core.read_model(mpath)
            configs = {}
            configs["NUM_STREAMS"] = 1
            configs["INFERENCE_PRECISION_HINT"] = args.prec
            compiled_model = core.compile_model(org_model, "CPU", configs)
            serialize(compiled_model.get_runtime_model(), exec_graph_fname)

            print(f"[exec graph] {mpath} is serialized to {exec_graph_fname}")
        
