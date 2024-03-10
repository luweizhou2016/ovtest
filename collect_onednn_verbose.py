import os,sys
import collections

def parse_nodes_into_list(node_file, stream_name='STREAM0'):
    model = ''
    recording = False
    nodes_verbose = {}
    nodes_list = []
    node_idx = 0
    print('Start parsing regressed nodes list from file {1} only on {0}.....'.format(stream_name, node_file))

    with open(node_file) as infile:
        for line in infile:
            if line.endswith('xml:\n'):
                if recording:
                    nodes_list.append((model, nodes_verbose))
                nodes_verbose = {}
                node_idx = 0
                model = line[:-2]
                recording = False
            elif line == f'{stream_name}:\n' and not recording:
                recording = True
            elif line.startswith('STREAM') and recording:
                nodes_list.append((model, nodes_verbose))
                model = ''
                nodes_verbose = {}
                recording = False
                node_idx = 0
            elif recording and line != '\n':
                nodes_verbose[node_idx] = [line.strip(), '', '']
                node_idx +=1

    if recording:
        nodes_list.append((model, nodes_verbose))
    return nodes_list

def record_onednn_verbose(nodes_list, dbg_dir ='debug_log'):
    for model, nodes_verbose in nodes_list:
        *x, ir = model.split('/')
        name,*x = ir.split('.')
        paths = [f'{os.getcwd()}{"/"}{dbg_dir}{"/"}{"ref_verbose_"}{name}{".txt"}' ,
                    f'{os.getcwd()}{"/"}{dbg_dir}{"/"}{"targ_verbose_"}{name}{".txt"}']
        for file_path in paths:
            is_ref = (file_path.find('ref_') != -1)
            ## list is [node_name, ref_onednn_verbose, targ_onednn_verbose]
            verbose_idx = 1 if is_ref else 2
            with open(file_path, 'r') as fp:
                for line in fp:
                    for idx, value in nodes_verbose.items():
                        token = f'{"##"}{value[0]}{"##"}'
                        pos = line.find(token)
                        if pos != -1 and value[verbose_idx] == "":
                            ###Once debuglogs is colleceted in tput mode(even not recommended), will not overwrite the verbose. 
                            ###In this case, only the stream0 verbose is collected for eaisness. In theory, all the stream would have same onednn verbose
                            ###even for hybrid platform.
                            ###@todo: analyze the feasibility and necessity to collect onednn verbose with spcified stream idx.
                            value[verbose_idx] = line[pos+len(token):-1]
    # print(len(node_list))
    verbose_file = f'{dbg_dir}/all_onednn_verbose.txt'
    print('Start recording onednn regressed verbose into {0}'.format(verbose_file))
    verbose_fp = open(verbose_file, 'w')
    for model, nodes_verbose in nodes_list:
        *x, ir = model.split('/')
        name,*x = ir.split('.')
        verbose_fp.write("Model:%s:\n" % name)
        sorted_nodes_verbose = collections.OrderedDict(sorted(nodes_verbose.items()))
        for idx, value in sorted_nodes_verbose.items():
            verbose_fp.write("@%s\n" % value[0])
            verbose_fp.write("%s\n" % value[1])
            verbose_fp.write("%s\n" % value[2])
        verbose_fp.write("\n")

    verbose_fp.close()

### Uncomment the below codes and run the command 'python3 ./get_verbose.py ./record' to test.
# record_dir = sys.argv[1]
# nodes_path = f'{record_dir}/nodes.txt'
# node_list = parse_nodes_into_list(nodes_path)
# record_onednn_verbose(node_list,  record_dir)
