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

## lpips_models

```bash
openvino/thirdparty/open_model_zoo/tools/accuracy_checker/openvino/tools/accuracy_checker/metrics/image_quality_assessment.py

@@ -466,7 +466,7 @@ class LPIPS(BaseRegressionMetric):
             if isinstance(weights, tuple):
                 weights = weights[1] if torch.__version__ <= '1.6.0' else weights[0]
             preloaded_weights = torch.utils.model_zoo.load_url(
-                weights, model_dir=model_dir, progress=False, map_location='cpu'
+                weights, model_dir="lpips_models", progress=False, map_location='cpu'
             )
         model = model_classes[net](pretrained=False)
         model.load_state_dict(preloaded_weights)

# do following
mkdir lpips_models
cd lpips_models
wget https://download.pytorch.org/models/alexnet-owt-7be5be79.pth
wget https://download.pytorch.org/models/alexnet-owt-4df8aa71.pth
wget https://download.pytorch.org/models/squeezenet1_1-b8a52dc0.pth
wget https://download.pytorch.org/models/vgg16-397923af.pth

```