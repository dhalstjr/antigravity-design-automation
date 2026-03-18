import os
from psd_tools import PSDImage
from PIL import Image
import json

def extract_psd_data(psd_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    psd = PSDImage.open(psd_path)
    layers_data = []

    def process_layers(layers, parent_group=None):
        for i, layer in enumerate(layers):
            layer_info = {
                "name": layer.name,
                "type": layer.kind,
                "left": layer.left,
                "top": layer.top,
                "width": layer.width,
                "height": layer.height,
                "visible": layer.visible,
                "opacity": layer.opacity,
                "parent": parent_group
            }
            
            # 텍스트 레이어인 경우 내용 추출
            if layer.kind == 'type':
                try:
                    layer_info["text"] = layer.text
                except:
                    layer_info["text"] = ""

            layers_data.append(layer_info)
            
            # 그룹인 경우 재귀적으로 처리
            if layer.is_group():
                process_layers(layer, layer.name)
            else:
                # 이미지 레이어인 경우 내보내기 (PNG)
                try:
                    layer_image = layer.composite()
                    img_path = os.path.join(output_dir, f"layer_{len(layers_data)}.png")
                    layer_image.save(img_path)
                    layer_info["image_path"] = img_path
                except Exception as e:
                    print(f"Error saving layer {layer.name}: {e}")

    process_layers(psd)
    
    # 데이터 저장
    with open(os.path.join(output_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(layers_data, f, indent=4, ensure_ascii=False)
    
    print(f"Extraction complete. Data saved in {output_dir}")

if __name__ == "__main__":
    # 예시 실행 (사용자가 파일을 주면 이 경로를 변경)
    # extract_psd_data("sample.psd", "output_assets")
    pass
