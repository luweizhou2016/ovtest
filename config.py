import sys
from pathlib import Path

base_path = Path(__file__).parent.absolute()

accuracy_checker_configs = []
accuracy_checker_configs.append("/home/openvino-local-compile-02/common_data/accuracy-checker/configs/")
accuracy_checker_configs.append(base_path.joinpath("./extern/frameworks.ai.openvino.accuracy-checker-configs/configs/omz_validation/"))
accuracy_checker_configs.append("./openvino/thirdparty/open_model_zoo/models/")

definitions_file = []
#definitions_file.append(base_path.joinpath("external_tools/frameworks.ai.openvino.accuracy-checker-configs/configs/omz_validation/datasets_definitions.yml"))
definitions_file.append("./extern/annotation_converters_ext/calibration_definitions.yml")

data_source=base_path.joinpath("./extern/omz-validation-datasets/")

model_attributes=f"{data_source}/model_attributes"

annotations=base_path.joinpath("./extern/annotations")

if __name__ == "__main__":
    #all_variables = dir()
    #print(eval(sys.argv[1]))
    print(__file__)
    print(accuracy_checker_configs)

