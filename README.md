# ovtest

## first time setup
```bash
./setup.sh ~/path/to/openvino
```


## test accuracy

```bash
./init.sh
python ./test_acc.py --model_list ./list_ww09_f32.txt -s 10
```