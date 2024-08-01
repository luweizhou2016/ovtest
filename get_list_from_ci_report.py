import sys

if len(sys.argv) <  2:
    print("Unsupported argument number!")
    print("get_list.py ci_list.txt full_list.txt ")
    sys.exit(0) 
if len(sys.argv) == 4:
    threshold = float(sys.argv[3])
else:
    threshold = float(95.0)
    

# Using readlines()
ci_file = open(sys.argv[1], 'r')
ci = ci_file.readlines()
all_model_file = open(sys.argv[2], 'r')
all = all_model_file.readlines()
# all the regressed list
outfile = open('all_out_list.txt', 'w')
# regressed list sorted by precision.
prec_dic = {"INT8" : "int8_out_list.txt", "FP16" : "fp16_out_list.txt", "FP32" : "fp32_out_list.txt"}

file_list = []
for k, v in prec_dic.items():
    f = open(v ,'w')
    file_list.append(list((k, f)))

# Strips the newline character
for ci_line in ci:
    ci_list = ci_line.split()
    try:
        gain = float(ci_list[8])
    except ValueError:
        print('Cannot convert string to float: '+ ci_line[:-1])
    if gain >= threshold:
        print(gain, threshold)
        continue
    for all_line in all:
        if (all_line.find('/'+ ci_list[3] + '/' + ci_list[4].lower()+'/') != -1 and all_line.find('/'+ci_list[5]+'/1/') != -1):
            outfile.write(all_line[:-1]+' ./configs/fp16/i3d-flow-tf.yml\n')
            for item in file_list:
                if ci_list[5] == item[0]:
                    item[1].write(all_line[:-1]+' ./configs/fp16/i3d-flow-tf.yml\n')

for item in file_list:
    item[1].close()
outfile.close()
all_model_file.close()
ci_file.close()
