import sys

idx_ir_perf = 0
idx_type_perf = 1
idx_node_perf = 2

idx_total_in_ir = 0
idx_avg_in_ir = 1

### return type is a list of list.
### return the[stream0_perf, stream1_perf, .....].
### each streamX_perf would be [graph perf, perf_by_types, perf_by_nodes],
def parse_raw_perf_data(in_file, token_list):
    if len(token_list) < 2:
        return[]
    multi_streams_perf = []
    stream_perf = []
    token_perf = []
    start_token = token_list[0]
    end_token = token_list[1]
    end_token_idx = 1

    line_in_stream = False
    line_in_token = False
    for line in in_file:
        if line.startswith('======= ENABLE_DEBUG_CAPS:OV_CPU_SUMMARY_PERF ======') and line_in_stream == False:
            line_in_stream = True
            line_in_token = False
        elif line_in_stream == False:
            continue
        ### else cases would all in stream perf buffer.
        if line.startswith(start_token) and line_in_token == False:
            token_perf = []
            stream_perf = []
            line_in_token = True
            end_token_idx = 1
        elif line_in_token == True and line.startswith(end_token):
            ## append perf data between tokens into stream perf
            stream_perf.append(token_perf)
            if end_token == token_list[-1]:
                ### one stream is ready
                line_in_stream = False
                ### append stream data into list. 
                multi_streams_perf.append(stream_perf)
                start_token = token_list[0]
                end_token = token_list[1]
                stream_perf = []
                token_perf = []

            else:
                end_token_idx += 1
                end_token = token_list[end_token_idx]
                token_perf = []
            # print(token_perf)
            # print(len(token_perf))
        elif line_in_token == True:
            # print(line)
            ### append per-node data
            token_perf.append(line.strip())
    return multi_streams_perf

### return nodes perf dic.
### key: node_name        
### value: list [perf_counter, precentage, implement_type]
def nodes_perf_in_dic(nodes_data):
    dic = {}
    for line in nodes_data:
        perc, x, perf, y, node_name, imp_type = line.split()
        counter,*x = perf.split('(')
        dic[node_name] = [float(counter), perc, imp_type]
    return dic

### return a list of [stream0_data, stream2_data,....]
### streamXdata: tuple of (nodes perf dic , average_time).
### nodes perf: return of nodes_perf_in_dic()
def get_perf(perf_file_path):
    token_list = ['Summary of ', ' perf_by_type:', ' perf_by_node:', 'perf_summary_end']
    with open(perf_file_path) as infile:
        raw_perf_streams = parse_raw_perf_data(infile, token_list)
    streams_perf = []
    for raw_perf_per_stream in raw_perf_streams:
        dic = nodes_perf_in_dic(raw_perf_per_stream[idx_node_perf])
        *a, avg_perf = raw_perf_per_stream[idx_ir_perf][idx_avg_in_ir].split()
        streams_perf.append((dic, float(avg_perf)))
    return streams_perf

def compare_perf(ref_path, target_path):
    targ_streams_perf = get_perf(target_path)
    ref_streams_perf = get_perf(ref_path)

    if len(targ_streams_perf) != len(ref_streams_perf):
        print('Error: target streams number is {0} , not equal with refrence streams number {1}'. format(len(targ_streams_perf), len(ref_streams_perf)))
        exit()
    topN_regression_dic = {}
    print(len(targ_streams_perf))
    for stream_idx in range(0, len(targ_streams_perf)):
        target_perf, target_avg = targ_streams_perf[stream_idx]
        ref_perf, ref_avg = ref_streams_perf[stream_idx]
        nodes_dic = {}
        new_nodes_dic = {}
        missing_nodes_dic = {}
        for x in target_perf.keys():
            targer_cnt = (target_perf[x])[0]
            if x in ref_perf:
                ref_cnt = (ref_perf[x])[0]
                nodes_dic[x] = targer_cnt - ref_cnt
            else:
                new_nodes_dic[x] = targer_cnt

        for x in ref_perf.keys():
            if not x in target_perf:
                ref_cnt = (ref_perf[x])[0]
                missing_nodes_dic[x] = ref_cnt

        sorted_regressed_nodes = dict(sorted(nodes_dic.items(), key=lambda item: item[1], reverse=True))
        sorted_gain_nodes = dict(sorted(nodes_dic.items(), key=lambda item: item[1]))

        sorted_new = dict(sorted(new_nodes_dic.items(), key=lambda item: item[1], reverse=True))
        sorted_missing = dict(sorted(missing_nodes_dic.items(), key=lambda item: item[1], reverse=True))

        # print(sorted_nodes)
        topN = 10
        topN_nodes = []
        node_num = 0
        print('================================================================================================================')
        print('############################################## STREAM ID: {0} ###############################################'.format(stream_idx))
        print('-----------------------------------------------------------------------------------------------------------------')
        print('@@@@ TOP {0} REGRESSED NODE LIST:'.format(topN))
        for name, cnt in sorted_regressed_nodes.items():
            if cnt > 0.0 and node_num < topN:
                t_cnt = (target_perf[name])[0]
                r_cnt = (ref_perf[name])[0]
                t_type = (target_perf[name])[-1]
                r_type = (ref_perf[name])[-1]
                ratio_in_avg = cnt * 100.0 / ref_avg
                ratio_with_ref = cnt * 100.0 / r_cnt

                print('Total: {0:^4.2f} % , {1:^12.1f}us @{4:^10} -> {2:^12.1f}us@{5:^10} : {3:^4.2f} % , {6:^20} '.format(ratio_in_avg, r_cnt, t_cnt, ratio_with_ref,  r_type, t_type, name))
                node_num += 1
                topN_nodes.append(name)
        topN_regression_dic[stream_idx] = topN_nodes
        print('-----------------------------------------------------------------------------------------------------------------')
        print('@@@@ TOP {0} PERF GAIN NODE LIST:'.format(topN))
        node_num = 0
        for name, cnt in sorted_gain_nodes.items():
            if cnt < 0.0 and node_num < topN:
                t_cnt = (target_perf[name])[0]
                r_cnt = (ref_perf[name])[0]
                t_type = (target_perf[name])[-1]
                r_type = (ref_perf[name])[-1]
                ratio_in_avg = cnt * 100.0 / ref_avg
                ratio_with_ref = cnt * 100.0 / r_cnt

                print('Total: {0:^4.2f} % , {1:^12.1f}us @{4:^10} -> {2:^12.1f}us@{5:^10} : {3:^4.2f} % , {6:^20} '.format(ratio_in_avg, r_cnt, t_cnt, ratio_with_ref,  r_type, t_type, name))
                node_num += 1
        print('-----------------------------------------------------------------------------------------------------------------')
        print('@@@@ NEW NODES LIST:')
        node_num = 0
        for name, cnt in sorted_new.items():
            if node_num < topN:
                t_cnt = (target_perf[name])[0]
                t_type = (target_perf[name])[-1]
                ratio_in_avg = cnt * 100.0 / ref_avg

                print('Total: {0:^4.2f} % , {1:^12.1f}us @{2:^10} , {3:^20} '.format(ratio_in_avg, t_cnt, t_type, name))
                node_num += 1
    return topN_regression_dic

### Uncomment the Direct debug with file inputs.
ref_path = sys.argv[1]
target_path = sys.argv[2]
compare_perf(ref_path, target_path)

