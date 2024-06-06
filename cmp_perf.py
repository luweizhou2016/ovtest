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
    token_idx = 0
    stream_start = False
    token_start = False
    for line in in_file:
        ## find the stream start token
        if line.startswith('======= ENABLE_DEBUG_CAPS:OV_CPU_SUMMARY_PERF ======'):
            if token_start:
                stream_perf.append(token_perf)
            if stream_start:
                multi_streams_perf.append(stream_perf)
            token_idx = 0
            stream_perf = []
            stream_start = True
            token_start = False
        elif stream_start == False:
            continue
        ##streams start = true case.
        if line.startswith(token_list[token_idx]):
            if token_start:
                ##Append last token recorded
                stream_perf.append(token_perf)
            token_perf = []
            token_start = True
            if (token_idx != len(token_list) - 1):
                token_idx += 1
        elif token_start:
            if line != '\n':
                token_perf.append(line.strip())
    ##Append the all the remaining data if having.
    if token_start:
        stream_perf.append(token_perf)
    if stream_start:
        multi_streams_perf.append(stream_perf)
    return multi_streams_perf

### convert the perf by nodes data into dictionary.
### return nodes perf dic.
### key: node_name        
### value: list [perf_counter, precentage, implement_type]
def nodes_perf_in_dic(nodes_data):
    dic = {}
    for line in nodes_data:
        # if (len(line.split()) > 6):
        #     print('!!!!!!len = {1}, expected 6, skip parsing perf "{0}"'.format(line, str(len(line.split()))))
        #     # continue
        split_perf = line.split()
        perc = split_perf[0]
        perf = split_perf[2]
        imp_type = split_perf[-1]
        if (len(split_perf) > 6):
            node_name = "".join(split_perf[4:-1])
        else:
            node_name = split_perf[4]
        #perc, x, perf, y, *node_name, imp_type = line.split()
        counter,*x = perf.split('(')
        dic[node_name] = [float(counter), perc, imp_type]
    return dic

### get all the streams perf by node.
### return a list of [stream0_data, stream2_data,....]
### streamXdata: tuple of (nodes perf dic , average_time).
### nodes perf: return of nodes_perf_in_dic()
def get_perf(perf_file_path):
    token_list = ['Summary of ', ' perf_by_type:', ' perf_by_node:']
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
stream_mark = '####################################################################################################################################################################'
data_mark = '-----------------------------------------------------------------------------------------------------------------------------------------------------------------'
### compare 2 perf file with  'OV_CPU_SUMMARY_PERF = 1'
### return a dic of regresssed node [stream_idx:topN_regressed_list]
def compare_perf(ref_path, target_path):
    targ_streams_perf = get_perf(target_path)
    ref_streams_perf = get_perf(ref_path)

    if len(targ_streams_perf) != len(ref_streams_perf):
        print('## target streams number is {0} , not equal with refrence streams number {1}. \n target file: {3}, ref file {2}:'. format(len(targ_streams_perf), len(ref_streams_perf), ref_path, target_path))
        return dict()
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
        missing_prec = sum(missing_dic.values()) * 100 / ref_avg

        # print(sorted_nodes)
        topN = 10
        topN_nodes = []
        node_num = 0
        print(stream_mark)
        print('@@@STREAM ID: {0} , Total regression: [{6:.0f}us -> {7:.0f}us,  {1:.3f}% ], Break down into 4 cases: ({2:.3f}%) + ({3:.3f}%) + ({4:.3f}%) + (-{8:.3f}%) = {5:.3f}% (regress - gain + new - missing)  '.format(stream_idx,
                                                                        total_regression_perc, nodes_regression_perc,
                                                                        nodes_gain_perc, new_regression_perc, nodes_regression_perc+nodes_gain_perc+new_regression_perc-missing_prec,
                                                                        ref_avg, target_avg, missing_prec))
        print(stream_mark)
### print the regressed node.
        print('TOP {0} REGRESSED NODE LIST:'.format(topN))
        impl_dic = dict();
        for name, cnt in sorted_regressed_nodes.items():
            t_type = (target_perf[name])[idx_impl_type_in_list]
            r_type = (ref_perf[name])[idx_impl_type_in_list]
            # The regressed count contribution to whole avg cnt
            perc_in_avg = cnt * 100.0 / ref_avg
            impl_key= f'{r_type}{"-->"}{t_type}'
            if impl_key in impl_dic.keys():
                impl_dic[impl_key] += perc_in_avg
            else:
                impl_dic[impl_key] = perc_in_avg

            if node_num < topN:
                t_cnt = (target_perf[name])[idx_perf_in_list]
                r_cnt = (ref_perf[name])[idx_perf_in_list]
                perc_with_ref = cnt * 100.0 / r_cnt
                print('node_diff/ref_total_latency: {0:<6.2f} % , {1:>12.0f}us @{4:<35} -> {2:>12.0f}us@{5:<35} : {3:<6.2f} % , {6:<20} '.format(perc_in_avg, r_cnt, t_cnt, perc_with_ref,  r_type, t_type, name))
                node_num += 1
                topN_nodes.append(name)
        impl_dic = dict(sorted(impl_dic.items(), key=lambda x: x[1], reverse=True))
        print('*****************************')
        print('All Regressed by type summary:')
        for key, val in impl_dic.items():
            print('{0:<100} : {1:<.2f}%'.format(key, val))
        topN_regression_dic[stream_idx] = topN_nodes

### print the gained node information
        print(data_mark)
        print('TOP {0} PERF GAIN NODE LIST:'.format(topN))
        impl_dic.clear()
        node_num = 0
        for name, cnt in sorted_gain_nodes.items():
            t_type = (target_perf[name])[idx_impl_type_in_list]
            r_type = (ref_perf[name])[idx_impl_type_in_list]
            # The regressed count contribution to whole avg cnt
            perc_in_avg = cnt * 100.0 / ref_avg
            impl_key= f'{r_type}{"-->"}{t_type}'
            if impl_key in impl_dic.keys():
                impl_dic[impl_key] += perc_in_avg
            else:
                impl_dic[impl_key] = perc_in_avg
            if node_num < topN:
                t_cnt = (target_perf[name])[idx_perf_in_list]
                r_cnt = (ref_perf[name])[idx_perf_in_list]
                perc_in_avg = cnt * 100.0 / ref_avg
                perc_with_ref = cnt * 100.0 / r_cnt

                print('node_diff/ref_total_latency: {0:<6.2f} % , {1:>12.0f}us @{4:<35} -> {2:>12.0f}us@{5:<35} : {3:<6.2f} % , {6:<20} '.format(perc_in_avg, r_cnt, t_cnt, perc_with_ref,  r_type, t_type, name))
                node_num += 1
        impl_dic = dict(sorted(impl_dic.items(), key=lambda x: x[1]))
        print('*****************************')
        print('All gain by type summary:')
        for key, val in impl_dic.items():
            print('{0:<100} : {1:<.2f}%'.format(key, val))
        topN_regression_dic[stream_idx] = topN_nodes

### print the missing node information
        print(data_mark)
        print('TOP {0} MISSING NODES LIST WITH THRESHOLD_PC > 5 :'.format(topN))
        node_num = 0
        for name, cnt in sorted_missing.items():
            if node_num < topN and cnt > 5 :
                t_cnt = (ref_perf[name])[idx_perf_in_list]
                t_type = (ref_perf[name])[idx_impl_type_in_list]
                perc_in_avg = cnt * 100.0 / ref_avg

                print('node_diff/ref_total_latency: {0:<6.2f} % , {1:>12.0f}us @{2:<35} , {3:<20} '.format(perc_in_avg, t_cnt, t_type, name))
                node_num += 1
        print(data_mark)
### print the new added node information
        print(data_mark)
        print('TOP {0} NEW NODES LIST WITH THRESHOLD_PC > 5 :'.format(topN))
        node_num = 0
        for name, cnt in sorted_new.items():
            if node_num < topN and cnt > 5 :
                t_cnt = (target_perf[name])[idx_perf_in_list]
                t_type = (target_perf[name])[idx_impl_type_in_list]
                perc_in_avg = cnt * 100.0 / ref_avg

                print('node_diff/ref_total_latency: {0:<6.2f} % , {1:>12.0f}us @{2:<35} , {3:<20} '.format(perc_in_avg, t_cnt, t_type, name))
                node_num += 1
        print(data_mark)

    print('\n')
    return topN_regression_dic

## Uncomment the Direct debug with file inputs.
# ref_path = sys.argv[1]
# target_path = sys.argv[2]
# node_list = compare_perf(ref_path, target_path)
# print(node_list)
# fp_nodes = open('./nodes.txt',  'w')


