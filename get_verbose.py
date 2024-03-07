import os,sys

def find(node_file, stream_idx='STREAM0'):
    model = ''
    recording = False
    nodes_verbose = {}
    nodes_list = []
    node_idx = 0
    with open(node_file) as infile:
        for line in infile:
            if line.endswith('xml:\n'):
                if recording:
                    nodes_list.append((model, nodes_verbose))
                nodes_verbose = {}
                node_idx = 0
                model = line[:-2]
                recording = False
            elif line == f'{stream_idx}:\n' and not recording:
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

def record_verbose(nodes_list, record_file, dbg_dir ='debug_log'):
    record_fp = open(record_file, 'a')
    for model, nodes_verbose in nodes_list:
        *x, ir = model.split('/')
        name,*x = ir.split('.')
        # record_fp.write(f'{"@"}{name}{"\n"}')
        paths = [f'{os.getcwd()}{"/"}{dbg_dir}{"/"}{"ref_verbose_"}{name}{".txt"}' ,
                    f'{os.getcwd()}{"/"}{dbg_dir}{"/"}{"targ_verbose_"}{name}{".txt"}']
        for file_path in paths:
            is_ref = (file_path.find('ref_') != -1)
            with open(file_path, 'r') as fp:
                for line in fp:
                    for idx, value in nodes_verbose.items():
                        token = f'{"##"}{value[0]}{"##"}'
                        pos = line.find(token)
                        if pos != -1:
                            list_idx = 1 if is_ref else 2
                            value[list_idx] = line[pos+len(token):-1]
  
    
#node_list = find('/home/luwei/ovtest/nodes.txt')
node_list = find('/home/luwei/ovtest/streams_nodes.txt')

record_verbose(node_list, './tmp.txt')
# print(node_list)
print(len(node_list))
