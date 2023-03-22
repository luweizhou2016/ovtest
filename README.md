# ovtest

## first time setup
```bash
./setup.sh ~/path/to/openvino
```

## generate list

```bash
source ./init.sh
python3 ./utils.py --collect ./extern/nfs_share_models/ww09_weekly_23.0.0-9828-4fd38844a28-API2.0-FP16  --to ./configs/fp16/
```

above command will generate list.txt which can be used by `./test_acc.py` and copies required yml configs into `./configs/fp16/`

## test accuracy on list

```bash
source ./init.sh
python ./test_acc.py --model_list ./list_ww09_f32.txt -s 10
```