import utils
import os,sys
import utils
import argparse
import re, math,config
import subprocess
import colorama
import shutil
from colorama import Fore
from cmp_perf import *
from collect_onednn_verbose import *

config_ref = {
    "bin_folder":"./openvino/bin_master/intel64/Release",
    "extra_options":"-infer_precision=f32",
    "extra_cmd":"",
}

config_tag = {
    "bin_folder":"./openvino/bin_3.5/intel64/Release",
    "extra_options":"-infer_precision=f32",
    "extra_cmd":"",
}

# dbg_dir = "debug_log"

def get_cmd(cfg, model_path, args):
    bin_folder = cfg['bin_folder']
    extra_cmd = cfg['extra_cmd']
    extra_options = cfg['extra_options']
    *x, ir = model_path.split('/')
    name,*y = ir.split('.')
    prec = "INT8" if x[-1] == "optimized" else x[-3]
    frame = x[-6] if x[-1] == "optimized" else x[-4]
    name = name + '_' + frame + '_' + prec
    log_file = ''
    is_ref = True
    is_perf = True
    dbg_dir = args.output_dir
    if bin_folder == config_ref['bin_folder']:
        is_ref = True
    else:
        is_ref = False
    if "perf" in args.debug:
        is_perf = True
    else:
        is_perf = False
    ## generate logging file name.
    log_file = f'{os.getcwd()}{"/"}{dbg_dir}{"/"}{"ref_" if is_ref else "targ_"}{"perf_" if is_perf else "verbose_"}{name}{".txt"}'
    if len(extra_cmd) == 0:
        extra_cmd = "echo"
    if is_perf:
        #### collect the perf information. need to run with some timing
        if args.tput:
            ## tee command to both saved into files and output to bash.
            return f"cd {bin_folder}; {extra_cmd}; /usr/bin/time -v ./benchmark_app -t {args.time} -hint=tput {extra_options} -m {model_path} | tee {log_file}"
        elif args.latency:
            return f"cd {bin_folder}; {extra_cmd}; /usr/bin/time -v ./benchmark_app -t {args.time} -hint=latency {extra_options} -m {model_path} | tee {log_file}"
        return f"cd {bin_folder}; {extra_cmd}; numactl -C 0,2,4,6,8,10,12,14 /usr/bin/time -v ./benchmark_app -t {args.time} -nstreams=2 -nthreads=4 -hint=none {extra_options} -m {model_path} | tee {log_file}"
    else:
        ### argument time would be ignored. Only infer once to collect logs.
        if args.tput:
            return f"cd {bin_folder}; {extra_cmd}; /usr/bin/time -v ./benchmark_app -niter 1 -hint=tput {extra_options} -m {model_path} | tee {log_file}"
        elif args.latency:
            return f"cd {bin_folder}; {extra_cmd}; /usr/bin/time -v ./benchmark_app -niter 1 -hint=latency {extra_options} -m {model_path} | tee {log_file}"
        return f"cd {bin_folder}; {extra_cmd}; numactl  -C  0,2,4,6,8,10,12,14  /usr/bin/time -v ./benchmark_app -niter 1 -nstreams=1 -nthreads=8 -hint=none {extra_options} -m {model_path} | tee {log_file}"

class info:
    pat = {
        "load":re.compile("\[ INFO \] Compile model took (\d*.?\d*) ms"),
        "latmin":re.compile("\[ INFO \]    Min:\s*(\d*.?\d*) ms"),
        "latavg":re.compile("\[ INFO \]    Average:\s*(\d*.?\d*) ms"),
        "tput":re.compile("\[ INFO \] Throughput:\s*(\d*.?\d*) FPS"),
        "build":re.compile("\[ INFO \] Build ................................. (.*)"),
        "cpu":re.compile("\s*Percent of CPU this job got: (\d*)%"),
        "rss":re.compile("\s*Maximum resident set size \(kbytes\):\s(\d*)"),
        "pagefaults":re.compile("\s*Minor \(reclaiming a frame\) page faults:\s(\d*)"),
        "vcs":re.compile("\s*Voluntary context switches:\s(\d*)"),
        "ivcs":re.compile("\s*Involuntary context switches:\s(\d*)"),
    }
    def __init__(self, log_text) -> None:
        self.build = []
        for k,v in info.pat.items():
            if (k != "build"):
                setattr(self, k, float ('nan'))
        for line in log_text.splitlines():
            for k,v in info.pat.items():
                m = v.match(line)
                if (m):
                    if (k == "build"):
                        self.build.append(m.group(1))
                        continue
                    setattr(self, k, float(m.group(1)))

    def __repr__(self) -> str:
        return f"load={self.load} tput={self.tput} rss={self.rss} cpu={self.cpu} pagefaults={self.pagefaults} vcs={self.vcs} ivcs={self.ivcs} latmin={self.latmin} latavg={self.latavg} build={self.build}"

class compare_info:
    def __init__(self, i0, i1) -> None:
        self.i0 = i0
        self.i1 = i1
        self.tput = (i1.tput/i0.tput)
        self.latmin = (i1.latmin/i0.latmin)
        self.latavg = (i1.latavg/i0.latavg)
        self.load = (i1.load/i0.load)
        self.rss = (i1.rss/i0.rss)
        if i0.cpu == 0.0:
            self.cpu = 1.0
        else:
            self.cpu = (i1.cpu/i0.cpu)
        self.pagefaults = (i1.pagefaults/i0.pagefaults)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Test performance")
    parser.add_argument("-f", "--name_filter", type=str, help="target model name filter", default="")
    parser.add_argument("-t","--time", type=int, help="seconds to test. -t would not work when --log=debug or --log=verbose", default=1)    
    parser.add_argument("--tput", action="store_true", help="use hint=tput instead of (1stream + 4threads)")
    parser.add_argument("--latency", action="store_true", help="use hint=latency instead of (1stream + 4threads)")
    parser.add_argument("--model_list", type=str, default="int8_models/ww06_list.txt")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument('--debug', nargs='+', type=str, help="onednn: only record onednn verbose, cpudbg: only record debuglog, perf: record perf and record regression nodes", default="perf")
    parser.add_argument('-o',"--output_dir", type=str, help="Folder of recorded files", default="debug_log")

    args = parser.parse_args()
    # os.environ["ONEDNN_MAX_CPU_ISA"]="AVX512_CORE"
    if ("onednn" in args.debug or "cpudbg" in args.debug) and args.tput:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! Will collect tput mode debug verbose.")
    if "onednn" in args.debug:
        os.environ["ONEDNN_VERBOSE"]="1"
    if "cpudbg" in args.debug:
        os.environ["OV_CPU_DEBUG_LOG"]="-"
    if "perf" in args.debug:
        os.environ["OV_CPU_SUMMARY_PERF"]="1"
        os.environ["OV_CPU_DEBUG_LOG"]=""
        os.environ["ONEDNN_VERBOSE"]="none"


    print(f"searching for xml models in {args.model_list}...")
    models = utils.get_models_xmlyml_from_list(args.model_list, args.name_filter)
    comm_prefix = utils.get_common_prefix([xml for xml,_ in models])

    models_list = []
    geomean_tput = 1.0
    geomean_load = 1.0
    geomean_rss = 1.0
    geomean_cnt = 0
    geomean_latavg = 1.0

    log_ref = ""
    dbg_dir = args.output_dir
    # Check whether the specified path exists or not
    # isExist = os.path.exists(dbg_dir)
    # if isExist:
    #     shutil.rmtree(dbg_dir)
    # os.makedirs(dbg_dir)

    isExist = os.path.exists(dbg_dir)
    if not isExist:
        os.makedirs(dbg_dir)
    def do_test(cfg, mpath, args, print_info = True):
        ret = None
        error_happens = False
        log_ref = ""
        try:
            cmdline = get_cmd(cfg, mpath, args)
            if args.verbose:
                print(cmdline)
            log_ref = subprocess.check_output(cmdline, shell=True, stderr=subprocess.STDOUT, encoding="utf-8")
        except:
            print(Fore.RED + f"{mpath} failed in {cfg}, skip" + Fore.RESET)
            print(log_ref)
            error_happens = True
            return None
        if args.verbose:
            print(log_ref)
        i0 = info(log_ref)
        if print_info:
            print(f"\t{i0}")
        if not ret:
            ret = i0
        return ret

    for i, (xml, _) in enumerate(models):
        mpath = f"{os.getcwd()}/{xml}"
        i0 = do_test(config_ref, mpath, args)
        if not i0:
            continue
        print(f"=> reference {i0}")
        i1 = do_test(config_tag, mpath, args)
        if not i1:
            continue
        print(f"=>    target {i1}")

        cmp = compare_info(i0, i1)

        geomean_tput *= cmp.tput
        geomean_load *= cmp.load
        geomean_rss *= cmp.rss
        geomean_cnt += 1
        geomean_latavg *= cmp.latavg

        # bigger is better
        def nocolored_ratio(prefix, ratio, bigger_better):
            return f"{prefix}:{ratio:.3f}"

        def colored_ratio(prefix, ratio, bigger_better):
            if bigger_better > 0:
                bigger_color = Fore.GREEN
                lower_clor = Fore.YELLOW
            else:
                bigger_color = Fore.YELLOW
                lower_clor = Fore.GREEN
            return (bigger_color if ratio > 1 else lower_clor) + f"{prefix}:{ratio:.3f}" + Fore.RESET

        def get_text(color_func, args):
            CF = color_func
            if args.latency:
                return f'{i:3d}/{len(models)} {" [ Improved ] " if cmp.latavg < 1 else "[Regression]"} {CF("latavg",cmp.latavg,-1)} {CF("tput", cmp.tput, 1)} {CF("load",cmp.load,-1)} {CF("rss",cmp.rss, -1)} {mpath[-len(comm_prefix):]}'
            else:
                return f'{i:3d}/{len(models)} {" [ Improved ] " if cmp.tput > 1 else "[Regression]"} {CF("tput", cmp.tput, 1)} {CF("latavg",cmp.latavg,-1)} {CF("load",cmp.load,-1)} {CF("rss",cmp.rss, -1)} {mpath[-len(comm_prefix):]}'
        s = get_text(colored_ratio, args)
        print(s)
        models_list.append([s, cmp])


    print("====================================================\n")
    print(f"models in folder: {comm_prefix}")
    def getTput(item):
        s, cmp = item
        return cmp.tput
    def getLatAvg(item):
        s, cmp = item
        return cmp.latavg
    if args.latency:
        models_list.sort(key=getLatAvg, reverse=False)
    else:
        models_list.sort(key=getTput, reverse=True)
    for s,cmp in models_list:
        print(s)

    print(f"geomean_tput = {geomean_tput ** (1/geomean_cnt):.3f}")
    print(f"geomean_latavg = {geomean_latavg ** (1/geomean_cnt):.3f}")
    print(f"geomean_load = {geomean_load ** (1/geomean_cnt):.3f}")
    print(f"geomean_rss = {geomean_rss ** (1/geomean_cnt):.3f}")


    if "perf" in args.debug:
        ### Record all the regressed node into node.txt
        regressed_nodes_file = f'{args.output_dir}{"/nodes.txt"}'
        fp_nodes = open(regressed_nodes_file,  'w')

        for i, (xml, _) in enumerate(models):
            *x, ir = xml.split('/')
            name,*y = ir.split('.')
            prec = "INT8" if x[-1] == "optimized" else x[-3]
            frame = x[-6] if x[-1] == "optimized" else x[-4]
            name = name + '_' + frame + '_' + prec
            log_ref = f'{os.getcwd()}{"/"}{dbg_dir}{"/"}{"ref_"}{"perf_"}{name}{".txt"}'
            log_targ = f'{os.getcwd()}{"/"}{dbg_dir}{"/"}{"targ_"}{"perf_"}{name}{".txt"}'
            print('&&& {0}'.format(xml))
            dic = compare_perf(log_ref, log_targ)
            fp_nodes.write("%s:\n" % xml)
            ### Errors happen:
            if len(dic) == 0:
                fp_nodes.write("##can't compare perf, error happens, check the file for detials:\n")
            else:
                for idx,nodes in dic.items():
                    fp_nodes.write("STREAM%d:\n" % idx)
                    for node in nodes:
                        fp_nodes.write("%s\n" % node)
            fp_nodes.write("\n")

        fp_nodes.close()
        print('Regressed nodes is recorded in the file of {0}'.format(regressed_nodes_file))
        ### Re-run benchmark_app to collect the log with OV_CPU_DEBUG_LOG=- under {args.output_dir} folder.
        args_verbose = args
        args_verbose.debug = 'cpudbg'
        os.environ["OV_CPU_DEBUG_LOG"]="-"
        os.environ["OV_CPU_SUMMARY_PERF"]=""
        print('Collecting with OV_CPU_DEBUG_LOG verbose in folder: {0}.........'.format(args.output_dir))
        if args_verbose.tput:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! Will collect cpu debug log in tput mode")
        for i, (xml, _) in enumerate(models):
            mpath = f"{os.getcwd()}/{xml}"
            i0 = do_test(config_ref, mpath, args_verbose, False)
            if not i0:
                continue
            i1 = do_test(config_tag, mpath, args_verbose, False)
            if not i1:
                continue
        print('Collection done')
        node_list_regressed = parse_nodes_into_list(regressed_nodes_file)
        record_onednn_verbose(node_list_regressed,  args.output_dir)


