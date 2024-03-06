import sys

## Raw perf related data index
idx_summary_token = 0
idx_perf_by_type_token = 1
idx_perf_by_node_token = 2

## Sub-index in summray 
idx_total_in_summary = 0
idx_avg_in_isummary = 1

### find the perf related data by token and pack raw data into list.
### return type is a list of list.
### return the[stream0_perf, stream1_perf, .....].
### each streamX_perf would be [graph perf, perf_by_types, perf_by_nodes],
def pack_raw_perf_data(in_file, token_list):
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

### convert the perf by nodes data into dictionary.
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

### get all the streams perf by node.
### return a list of [stream0_data, stream2_data,....]
### streamXdata: tuple of (nodes perf dic , average_time).
### nodes perf: return of nodes_perf_in_dic()
def get_perf(perf_file_path):
    token_list = ['Summary of ', ' perf_by_type:', ' perf_by_node:', 'perf_summary_end']
    with open(perf_file_path) as infile:
        raw_perf_streams = pack_raw_perf_data(infile, token_list)
    streams_perf = []
    for raw_perf_per_stream in raw_perf_streams:
        dic = nodes_perf_in_dic(raw_perf_per_stream[idx_perf_by_node_token])
        *a, avg_perf = raw_perf_per_stream[idx_summary_token][idx_avg_in_isummary].split()
        streams_perf.append((dic, float(avg_perf)))
    return streams_perf


###  idx in the [perf_counter, precentage, implement_type]
idx_perf_in_list = 0
idx_perc_in_list = 1
idx_impl_type_in_list = 2
stream_token = '####################################################################################################################################################################'
list_token = '-----------------------------------------------------------------------------------------------------------------------------------------------------------------'
### compare 2 perf file with  'OV_CPU_SUMMARY_PERF = 1'
### return a dic of regresssed node [stream_idx:topN_regressed_list]
def compare_perf(ref_path, target_path):
    targ_streams_perf = get_perf(target_path)
    ref_streams_perf = get_perf(ref_path)

    if len(targ_streams_perf) != len(ref_streams_perf):
        print('Error: target streams number is {0} , not equal with refrence streams number {1}'. format(len(targ_streams_perf), len(ref_streams_perf)))
        exit()
    topN_regression_dic = {}
    # print(len(targ_streams_perf))
    for stream_idx in range(0, len(targ_streams_perf)):
        target_perf, target_avg = targ_streams_perf[stream_idx]
        ref_perf, ref_avg = ref_streams_perf[stream_idx]
        ### changed_dic: nodes both in ref and target
        ### new_dic: in target not in ref
        ### missing_dic: in ref not in target
        changed_dic = {}
        new_dic = {}
        missing_dic = {}
        for x in target_perf.keys():
            targer_cnt = (target_perf[x])[idx_perf_in_list]
            if x in ref_perf:
                ref_cnt = (ref_perf[x])[idx_perf_in_list]
                changed_dic[x] = targer_cnt - ref_cnt
            else:
                new_dic[x] = targer_cnt

        for x in ref_perf.keys():
            if not x in target_perf:
                ref_cnt = (ref_perf[x])[idx_perf_in_list]
                missing_dic[x] = ref_cnt

        sorted_regressed_nodes = {k:v for k,v in changed_dic.items() if v > 1.0}
        sorted_gain_nodes = {k:v for k,v in changed_dic.items() if v < -1.0}

        sorted_regressed_nodes = dict(sorted(sorted_regressed_nodes.items(), key=lambda item: item[1], reverse=True))
        ##gain counter are negative floating. No reverse mean top gain in the first.
        sorted_gain_nodes = dict(sorted(sorted_gain_nodes.items(), key=lambda item: item[1]))

        sorted_new = dict(sorted(new_dic.items(), key=lambda item: item[1], reverse=True))
        sorted_missing = dict(sorted(missing_dic.items(), key=lambda item: item[1], reverse=True))

        total_regression_perc = (target_avg - ref_avg) * 100.0 / ref_avg
        nodes_regression_perc = sum(sorted_regressed_nodes.values()) * 100 / ref_avg
        nodes_gain_perc = sum(sorted_gain_nodes.values()) * 100 / ref_avg

        new_regression_perc = sum(new_dic.values()) * 100 / ref_avg
        # print(sorted_nodes)
        topN = 10
        topN_nodes = []
        node_num = 0
        print('\n')
        print(stream_token)
        print(' STREAM ID: {0} , Total regression: [{6:.0f}us -> {7:.0f}us,  {1:.3f}% ], Breakdown in 3 cases: ({2:.3f}%) + ({3:.3f}%) + ({4:.3f}%) = {5:.3f}% (regress + gain + new)  '.format(stream_idx, total_regression_perc, nodes_regression_perc,
                                                                        nodes_gain_perc, new_regression_perc, nodes_regression_perc+nodes_gain_perc+new_regression_perc, ref_avg, target_avg))
        print(stream_token)

        print('@@@@ TOP {0} REGRESSED NODE LIST:'.format(topN))
        for name, cnt in sorted_regressed_nodes.items():
            if node_num < topN:
                t_cnt = (target_perf[name])[idx_perf_in_list]
                r_cnt = (ref_perf[name])[idx_perf_in_list]
                t_type = (target_perf[name])[idx_impl_type_in_list]
                r_type = (ref_perf[name])[idx_impl_type_in_list]
                perc_in_avg = cnt * 100.0 / ref_avg
                perc_with_ref = cnt * 100.0 / r_cnt

                print('Node regressed by: {0:<6.2f} % , {1:>12.0f}us @{4:<35} -> {2:>12.0f}us@{5:<35} : {3:<6.2f} % , {6:>20} '.format(perc_in_avg, r_cnt, t_cnt, perc_with_ref,  r_type, t_type, name))
                node_num += 1
                topN_nodes.append(name)
        topN_regression_dic[stream_idx] = topN_nodes
        print(list_token)
        print('@@@@ TOP {0} PERF GAIN NODE LIST:'.format(topN))
        node_num = 0
        for name, cnt in sorted_gain_nodes.items():
            if node_num < topN:
                t_cnt = (target_perf[name])[idx_perf_in_list]
                r_cnt = (ref_perf[name])[idx_perf_in_list]
                t_type = (target_perf[name])[idx_impl_type_in_list]
                r_type = (ref_perf[name])[idx_impl_type_in_list]
                perc_in_avg = cnt * 100.0 / ref_avg
                perc_with_ref = cnt * 100.0 / r_cnt

                print('Node regressed by: {0:<6.2f} % , {1:>12.0f}us @{4:<35} -> {2:>12.0f}us@{5:<35} : {3:<6.2f} % , {6:>20} '.format(perc_in_avg, r_cnt, t_cnt, perc_with_ref,  r_type, t_type, name))
                node_num += 1
        print(list_token)
        print('@@@@ TOP {0} NEW NODES LIST WITH THRESHOLD_PC > 5 :'.format(topN))
        node_num = 0
        for name, cnt in sorted_new.items():
            if node_num < topN and cnt > 5 :
                t_cnt = (target_perf[name])[idx_perf_in_list]
                t_type = (target_perf[name])[idx_impl_type_in_list]
                perc_in_avg = cnt * 100.0 / ref_avg

                print('Node regressed by: {0:<6.2f} % , {1:>12.0f}us @{2:<35} , {3:>20} '.format(perc_in_avg, t_cnt, t_type, name))
                node_num += 1
        print(list_token)

    return topN_regression_dic

### Uncomment the Direct debug with file inputs.
ref_path = sys.argv[1]
target_path = sys.argv[2]
compare_perf(ref_path, target_path)

