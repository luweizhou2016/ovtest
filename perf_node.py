import sys

def parse_data_list_from_file(in_file, token_list):
    if len(token_list) < 2:
        return[]
    stream_list = []
    buffer_list = []
    buffer = []
    pos_end = 1
    start_token = token_list[0]
    end_token = token_list[1]

    stream_token_found = False
    perf_token = False
    for line in in_file:
        if line.startswith('======= ENABLE_DEBUG_CAPS:OV_CPU_SUMMARY_PERF ======') and stream_token_found == False:
            stream_token_found = True
            perf_token = False
        elif stream_token_found == False:
            continue
        ###in stream buffer
        if line.startswith(start_token) and perf_token == False:
            buffer = []
            buffer_list = []
            perf_token = True
            pos_end = 1
        elif perf_token == True and line.startswith(end_token):
            buffer_list.append(buffer)
            if end_token == token_list[-1]:
                stream_token_found = False
                stream_list.append(buffer_list)
                start_token = token_list[0]
                end_token = token_list[1]
                buffer_list = []
                buffer = []

            else:
                pos_end += 1
                end_token = token_list[pos_end]
                buffer = []
            # print(buffer)
            # print(len(buffer))
        elif perf_token == True:
            # print(line)
            buffer.append(line.strip())
    return stream_list

def get_per_node_perf(node_data):
    dic = {}
    for line in node_data:
        perc, x, perf, y, node_name, imp_type = line.split()
        counter,*x = perf.split('(')
        dic[node_name] = [float(counter), perc, imp_type]
    return dic

def perf_from_file(perf_file_path):
    token_list = ['Summary of ', ' perf_by_type:', ' perf_by_node:', 'perf_summary_end']
    with open(perf_file_path) as infile:
        stream_buffer = parse_data_list_from_file(infile, token_list)
    stream_list = []
    for buffer in stream_buffer:
        dic = get_per_node_perf(buffer[2])
        *a, avg = buffer[0][1].split()
        stream_list.append((dic, float(avg)))
    return stream_list

def compare_perf_file(ref_path, target_path):
    target_stream_list = perf_from_file(target_path)
    ref_stream_list = perf_from_file(ref_path)

    if len(target_stream_list) != len(ref_stream_list):
        print('Error')
        exit()
    topN_regression_dic = {}
    print(len(target_stream_list))
    for stream_idx in range(0, len(target_stream_list)):
        target_perf, target_avg = target_stream_list[stream_idx]
        ref_perf, ref_avg = ref_stream_list[stream_idx]
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
compare_perf_file(ref_path, target_path)

